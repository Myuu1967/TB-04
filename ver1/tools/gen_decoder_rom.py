#!/usr/bin/env python3
"""
デコーダ ROM データ生成ツール（TB-04 4bitCPU）

アドレス構成（10bit = 1024エントリ）:
  A0-A3 : OPC[3:0]   （OPC[0]=A0）
  A4-A7 : OPR[3:0]   （OPR[0]=A4、i=[3:2]+j=[1:0] または即値/アドレス）
  A8    : C_prev      （74HC74ラッチ済みキャリー）
  A9    : Z_prev      （74HC74ラッチ済みゼロフラグ）
  A10-A14: GND

出力ビット構成:
  U22: D0-D2=WR_SEL[2:0], D3-D5=RD_SEL_A[2:0], D6-D7=RD_SEL_B[1:0]（下位2bit）
  U23: D0=RD_SEL_B[2]（上位1bit）, D1-D4=AluCode[3:0], D5=/WE, D6=NOT_JMP, D7=0
"""

import os

# MUX セレクタ定数
SEL_R0     = 0
SEL_R1     = 1
SEL_R2     = 2
SEL_R3     = 3
# 4, 5: 空き（ACC予約）
SEL_OPR_PC = 6   # 読み出し: 即値(OPR) / 書き込み: PC
SEL_IN_OUT = 7   # 読み出し: INポート / 書き込み: OUTポート

# ALU コード
ALU_NOP      = 0
ALU_PASS_A   = 1
ALU_AND      = 2
ALU_OR       = 3
ALU_XOR      = 4
ALU_ADD      = 5
ALU_SUB      = 6
ALU_SUBR     = 7
ALU_PASS_A_Z = 8  # IN命令用: y=a, C=0, Z=(y==0)

OPC_NAMES = [
    "NOP", "MOV",  "MOVI", "OUT",  "OUTI", "IN",   "JMP",  "JNC",
    "JZ",  "AND",  "OR",   "XOR",  "ADD",  "ADDI", "SUB",  "SUBI",
]


def decode(opc, opr, c_prev, z_prev):
    """
    デコーダ出力を返す:
      (wr_sel, rd_sel_a, rd_sel_b, we_n, alu_code, not_jmp)
    """
    i = (opr >> 2) & 0x3   # OPR[3:2]: Ri（書き込み先 / 演算先レジスタ）
    j = (opr >> 0) & 0x3   # OPR[1:0]: Rj（読み出し元レジスタ）

    if opc == 0:    # NOP
        return (0, 0, 0, 1, ALU_NOP, 1)

    elif opc == 1:  # MOV Ri, Rj
        return (i, j, 0, 0, ALU_PASS_A, 1)

    elif opc == 2:  # MOVI R0, Im
        return (SEL_R0, SEL_OPR_PC, 0, 0, ALU_PASS_A, 1)

    elif opc == 3:  # OUT Ri
        return (SEL_IN_OUT, i, 0, 0, ALU_PASS_A, 1)

    elif opc == 4:  # OUTI Im
        return (SEL_IN_OUT, SEL_OPR_PC, 0, 0, ALU_PASS_A, 1)

    elif opc == 5:  # IN Ri
        return (i, SEL_IN_OUT, 0, 0, ALU_PASS_A_Z, 1)

    elif opc == 6:  # JMP Addr
        return (SEL_OPR_PC, SEL_OPR_PC, 0, 0, ALU_PASS_A, 0)

    elif opc == 7:  # JNC Addr
        if c_prev == 0:  # C=0: ジャンプ実行
            return (SEL_OPR_PC, SEL_OPR_PC, 0, 0, ALU_PASS_A, 0)
        else:            # C=1: スキップ
            return (0, 0, 0, 1, ALU_NOP, 1)

    elif opc == 8:  # JZ Addr
        if z_prev == 1:  # Z=1: ジャンプ実行
            return (SEL_OPR_PC, SEL_OPR_PC, 0, 0, ALU_PASS_A, 0)
        else:            # Z=0: スキップ
            return (0, 0, 0, 1, ALU_NOP, 1)

    elif opc == 9:   # AND Ri, Rj
        return (i, i, j, 0, ALU_AND, 1)

    elif opc == 10:  # OR Ri, Rj
        return (i, i, j, 0, ALU_OR, 1)

    elif opc == 11:  # XOR Ri, Rj
        return (i, i, j, 0, ALU_XOR, 1)

    elif opc == 12:  # ADD Ri, Rj
        return (i, i, j, 0, ALU_ADD, 1)

    elif opc == 13:  # ADDI R0, Im  (b入力=R0、即値はa入力経由)
        return (SEL_R0, SEL_OPR_PC, SEL_R0, 0, ALU_ADD, 1)

    elif opc == 14:  # SUB Ri, Rj
        return (i, i, j, 0, ALU_SUB, 1)

    elif opc == 15:  # SUBI R0, Im  (b入力=R0、即値はa入力経由)
        return (SEL_R0, SEL_OPR_PC, SEL_R0, 0, ALU_SUBR, 1)

    else:
        return (0, 0, 0, 1, ALU_NOP, 1)


def pack_u15(wr_sel, rd_sel_a, rd_sel_b):
    """U15: D0-D2=WR_SEL[2:0], D3-D5=RD_SEL_A[2:0], D6-D7=RD_SEL_B[1:0]"""
    return (wr_sel & 0x7) | ((rd_sel_a & 0x7) << 3) | ((rd_sel_b & 0x3) << 6)


def pack_u19(rd_sel_b, alu_code, we_n, not_jmp):
    """U19: D0=RD_SEL_B[2], D1-D4=AluCode[3:0], D5=/WE, D6=NOT_JMP, D7=0"""
    return ((rd_sel_b >> 2) & 0x1) | ((alu_code & 0xF) << 1) | ((we_n & 1) << 5) | ((not_jmp & 1) << 6)


def generate_rom():
    """1024バイト × 2 のデコーダ ROM データを生成する。"""
    rom_u15 = bytearray(1024)
    rom_u19 = bytearray(1024)

    for z_prev in range(2):
        for c_prev in range(2):
            for opr in range(16):
                for opc in range(16):
                    addr = opc | (opr << 4) | (c_prev << 8) | (z_prev << 9)
                    wr, rd_a, rd_b, we_n, alu, not_jmp = decode(opc, opr, c_prev, z_prev)
                    rom_u15[addr] = pack_u15(wr, rd_a, rd_b)
                    rom_u19[addr] = pack_u19(rd_b, alu, we_n, not_jmp)

    return rom_u15, rom_u19


def write_bin(data, path):
    with open(path, 'wb') as f:
        f.write(data)
    print(f"BIN 出力: {path}  ({len(data)} bytes)")


def write_intel_hex(data, path, base_addr=0x0000):
    with open(path, 'w') as f:
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            n = len(chunk)
            addr = base_addr + i
            chk = n + (addr >> 8) + (addr & 0xFF)
            line = ''
            for b in chunk:
                line += f'{b:02X}'
                chk += b
            chk = ((~chk) + 1) & 0xFF
            f.write(f':{n:02X}{addr:04X}00{line}{chk:02X}\n')
        f.write(':00000001FF\n')
    print(f"HEX 出力: {path}  ({len(data)} bytes)")


def spot_check(rom_u15, rom_u19):
    cases = [
        # (opc, opr,    c, z,  ew, ea, eb, ewe, ealu,       enj, ラベル)
        (0,  0b0000, 0, 0,   0,  0,  0,   1, ALU_NOP,    1, "NOP"),
        (1,  0b1001, 0, 0,   2,  1,  0,   0, ALU_PASS_A, 1, "MOV R2,R1"),
        (2,  0b0101, 0, 0,   0,  6,  0,   0, ALU_PASS_A, 1, "MOVI R0,5"),
        (3,  0b1000, 0, 0,   7,  2,  0,   0, ALU_PASS_A, 1, "OUT R2"),
        (4,  0b0011, 0, 0,   7,  6,  0,   0, ALU_PASS_A, 1, "OUTI 3"),
        (5,  0b1100, 0, 0,   3,  7,  0,   0, ALU_PASS_A_Z, 1, "IN R3"),
        (6,  0b1010, 0, 0,   6,  6,  0,   0, ALU_PASS_A, 0, "JMP 0xA"),
        (7,  0b0110, 0, 0,   6,  6,  0,   0, ALU_PASS_A, 0, "JNC 0x6, C=0 → jump"),
        (7,  0b0110, 1, 0,   0,  0,  0,   1, ALU_NOP,    1, "JNC 0x6, C=1 → skip"),
        (8,  0b1110, 0, 0,   0,  0,  0,   1, ALU_NOP,    1, "JZ  0xE, Z=0 → skip"),
        (8,  0b1110, 0, 1,   6,  6,  0,   0, ALU_PASS_A, 0, "JZ  0xE, Z=1 → jump"),
        (9,  0b1001, 0, 0,   2,  2,  1,   0, ALU_AND,    1, "AND R2,R1"),
        (10, 0b0110, 0, 0,   1,  1,  2,   0, ALU_OR,     1, "OR  R1,R2"),
        (11, 0b1100, 0, 0,   3,  3,  0,   0, ALU_XOR,    1, "XOR R3,R0"),
        (12, 0b0110, 0, 0,   1,  1,  2,   0, ALU_ADD,    1, "ADD R1,R2"),
        (13, 0b0111, 0, 0,   0,  6,  0,   0, ALU_ADD,    1, "ADDI R0,7  (RD_B=R0)"),
        (14, 0b1101, 0, 0,   3,  3,  1,   0, ALU_SUB,    1, "SUB R3,R1"),
        (15, 0b1001, 0, 0,   0,  6,  0,   0, ALU_SUBR,   1, "SUBI R0,9  (RD_B=R0)"),
    ]

    print("\n=== スポットチェック ===")
    all_ok = True
    for opc, opr, c, z, ew, ea, eb, ewe, ealu, enj, label in cases:
        addr = opc | (opr << 4) | (c << 8) | (z << 9)
        b15 = rom_u15[addr]
        b19 = rom_u19[addr]
        wr   =  b15        & 0x7
        rd_a = (b15 >> 3)  & 0x7
        rd_b_lo = (b15 >> 6) & 0x3
        rd_b_hi = b19 & 0x1
        rd_b = rd_b_lo | (rd_b_hi << 2)
        alu  = (b19 >> 1) & 0xF
        we_n = (b19 >> 5) & 0x1
        nj   = (b19 >> 6) & 0x1
        ok = (wr == ew and rd_a == ea and rd_b == eb and
              we_n == ewe and alu == ealu and nj == enj)
        if not ok:
            all_ok = False
        status = "OK" if ok else "NG"
        print(f"  [{status}] {label:32s}  "
              f"WR={wr} RDA={rd_a} RDB={rd_b} /WE={we_n} ALU={alu} NJ={nj}")

    print()
    print("全ケース OK" if all_ok else "NG があります — 仕様を確認してください")


if __name__ == '__main__':
    out_dir = os.path.dirname(os.path.abspath(__file__))

    rom_u15, rom_u19 = generate_rom()

    write_bin(rom_u15, os.path.join(out_dir, 'decoder_u22.bin'))
    write_bin(rom_u19, os.path.join(out_dir, 'decoder_u23.bin'))
    write_intel_hex(rom_u15, os.path.join(out_dir, 'decoder_u22.hex'))
    write_intel_hex(rom_u19, os.path.join(out_dir, 'decoder_u23.hex'))

    spot_check(rom_u15, rom_u19)
