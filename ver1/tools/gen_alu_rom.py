#!/usr/bin/env python3
"""
ALU ROM データ生成ツール（TB-04 4bitCPU）

アドレス構成（12bit = 4096エントリ）:
  A0-A3  : a       (ALU入力a)
  A4-A7  : b       (ALU入力b)
  A8-A11 : alu_code (演算コード)

出力バイト構成:
  D0-D3 : y   (演算結果 4bit)
  D4    : C   (キャリーフラグ: 0=ボロー)
  D5    : Z   (ゼロフラグ: 1=結果が0)
  D6-D7 : 0   (未使用)
"""

import os

# ALU演算コード定義
NOP    = 0  # y = 0
PASS_A = 1  # y = a
AND    = 2  # y = a & b
OR     = 3  # y = a | b
XOR    = 4  # y = a ^ b
ADD    = 5  # y = a + b
SUB    = 6  # y = a - b  (C=0: ボロー)
SUBR   = 7  # y = b - a  (C=0: ボロー)
PASS_A_Z = 8  # y = a, C=0, Z=(y==0)  IN命令用
# 9-15: 予約 (出力0)

ALU_NAMES = ["NOP", "PASS_A", "AND", "OR", "XOR", "ADD", "SUB", "SUBR", "PASS_A_Z"] + ["RSVD"] * 7


def alu_compute(alu_code, a, b):
    """ALU演算を計算し (y, C, Z) を返す。"""
    a &= 0xF
    b &= 0xF

    if alu_code == NOP:
        y, C = 0, 0
    elif alu_code == PASS_A:
        y, C = a, 0
    elif alu_code == PASS_A_Z:
        y, C = a, 0
    elif alu_code == AND:
        y, C = a & b, 0
    elif alu_code == OR:
        y, C = a | b, 0
    elif alu_code == XOR:
        y, C = a ^ b, 0
    elif alu_code == ADD:
        r = a + b
        y, C = r & 0xF, (r >> 4) & 1
    elif alu_code == SUB:
        # a - b = a + (~b & 0xF) + 1 （2の補数加算）
        r = a + ((~b) & 0xF) + 1
        y, C = r & 0xF, (r >> 4) & 1
    elif alu_code == SUBR:
        # b - a = b + (~a & 0xF) + 1 （2の補数加算）
        r = b + ((~a) & 0xF) + 1
        y, C = r & 0xF, (r >> 4) & 1
    else:
        y, C = 0, 0  # 予約

    # NOP/PASS_A は Z に触らない（0固定）、それ以外は演算結果から決定
    Z = 0 if alu_code in (NOP, PASS_A) else (1 if y == 0 else 0)
    return y, C, Z


def generate_rom():
    """4096バイトのALU ROMデータを生成する。"""
    rom = bytearray(4096)
    for alu_code in range(16):
        for b in range(16):
            for a in range(16):
                addr = a | (b << 4) | (alu_code << 8)
                y, C, Z = alu_compute(alu_code, a, b)
                rom[addr] = y | (C << 4) | (Z << 5)
    return rom


def write_bin(rom, path):
    with open(path, "wb") as f:
        f.write(rom)
    print(f"BIN 出力: {path}  ({len(rom)} bytes)")


def write_intel_hex(rom, path, base_addr=0x0000):
    """Intel HEX形式で書き出す。"""
    with open(path, "w") as f:
        for i in range(0, len(rom), 16):
            chunk = rom[i : i + 16]
            n = len(chunk)
            addr = base_addr + i
            chk = n + (addr >> 8) + (addr & 0xFF)
            data = ""
            for byte in chunk:
                data += f"{byte:02X}"
                chk += byte
            chk = ((~chk) + 1) & 0xFF
            f.write(f":{n:02X}{addr:04X}00{data}{chk:02X}\n")
        f.write(":00000001FF\n")
    print(f"HEX 出力: {path}  ({len(rom)} bytes)")


def spot_check(rom):
    """代表ケースで動作確認。"""
    cases = [
        # (alu_code, a, b, 期待y, 期待C, 期待Z, ラベル)
        (PASS_A,   0x5, 0x0, 0x5, 0, 0, "PASS_A   a=5"),
        (PASS_A,   0x0, 0x0, 0x0, 0, 0, "PASS_A   a=0 → Z=0（不変扱い）"),
        (PASS_A_Z, 0x5, 0x0, 0x5, 0, 0, "PASS_A_Z a=5 → Z=0"),
        (PASS_A_Z, 0x0, 0x0, 0x0, 0, 1, "PASS_A_Z a=0 → Z=1"),
        (AND,    0xA, 0xC, 0x8, 0, 0, "AND  0xA & 0xC = 0x8"),
        (OR,     0xA, 0x5, 0xF, 0, 0, "OR   0xA | 0x5 = 0xF"),
        (XOR,    0xF, 0xF, 0x0, 0, 1, "XOR  0xF ^ 0xF = 0x0 (Z=1)"),
        (ADD,    0x3, 0x5, 0x8, 0, 0, "ADD  3+5=8"),
        (ADD,    0xF, 0x1, 0x0, 1, 1, "ADD  15+1=0 (C=1, Z=1)"),
        (ADD,    0xF, 0xF, 0xE, 1, 0, "ADD  15+15=14 (C=1)"),
        (SUB,    0x5, 0x3, 0x2, 1, 0, "SUB  5-3=2 (C=1)"),
        (SUB,    0x3, 0x5, 0xE, 0, 0, "SUB  3-5=14 (borrow C=0)"),
        (SUB,    0x5, 0x5, 0x0, 1, 1, "SUB  5-5=0 (C=1, Z=1)"),
        (SUBR,   0x3, 0x5, 0x2, 1, 0, "SUBR 5-3=2 (C=1)"),
        (NOP,    0x7, 0x3, 0x0, 0, 0, "NOP  y=0 → Z=0（不変扱い）"),
    ]

    print("\n=== スポットチェック ===")
    all_ok = True
    for code, a, b, ey, eC, eZ, label in cases:
        y, C, Z = alu_compute(code, a, b)
        addr = a | (b << 4) | (code << 8)
        ok = (y == ey and C == eC and Z == eZ)
        status = "OK" if ok else "NG"
        if not ok:
            all_ok = False
        print(f"  [{status}] {label:30s}  y={y:X} C={C} Z={Z}  addr=0x{addr:03X} byte=0x{rom[addr]:02X}")

    print()
    if all_ok:
        print("全ケース OK")
    else:
        print("NG があります — 仕様を確認してください")


def print_table(rom, alu_code):
    """指定演算コードの真理値表を表示する（デバッグ用）。"""
    name = ALU_NAMES[alu_code]
    print(f"\n=== {name} (code={alu_code}) ===")
    print("     b:", "  ".join(f"{b:X}" for b in range(16)))
    for a in range(16):
        row = []
        for b in range(16):
            addr = a | (b << 4) | (alu_code << 8)
            row.append(f"{rom[addr] & 0xF:X}")
        print(f"  a={a:X}: {'  '.join(row)}")


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    bin_path = os.path.join(out_dir, "alu_rom.bin")
    hex_path = os.path.join(out_dir, "alu_rom.hex")

    rom = generate_rom()
    write_bin(rom, bin_path)
    write_intel_hex(rom, hex_path)
    spot_check(rom)

    # ADD / SUB の真理値表をサンプル表示
    print_table(rom, ADD)
    print_table(rom, SUB)
