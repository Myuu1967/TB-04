"""tanuki 4bit CPU コアシミュレータ

注意: このシミュレータは命令単位モデル（1 step = 1命令を最後まで実行）で、
クロック/フェーズ（WB→FCH→DCR→EXE）はモデル化していない。
ジャンプは step() 内で即座に PC へ反映されるため、ディレイスロットは存在しない。
→ 実機の新フェーズ構成（2026-06-15: ディレイスロットなし・ジャンプ4クロック）と
   挙動が一致する。クロック単位の観測が必要なら別途フェーズ精密モデルが必要。
"""

# ALU 演算コード
ALU_NOP   = 0  # y = 0
ALU_PASSA = 1  # y = a
ALU_AND   = 2  # y = a & b
ALU_OR    = 3  # y = a | b
ALU_XOR   = 4  # y = a ^ b
ALU_ADD   = 5  # y = a + b
ALU_SUB   = 6  # y = a - b  (2の補数加算、C=0 がボロー)
ALU_SUBR  = 7  # y = b - a  (SUBI 用)

# MUX セレクタ（読み出し側）
MUX_R0  = 0
MUX_R1  = 1
MUX_R2  = 2
MUX_R3  = 3
MUX_OPR = 6   # 即値 / アドレス
MUX_IN  = 7   # IN ポート

# MUX セレクタ（書き込み側）
MUX_PC  = 6   # PC（ジャンプ先）
MUX_OUT = 7   # OUT ポート

# OPC 定義
OPC_NOP  = 0
OPC_MOV  = 1
OPC_MOVI = 2
OPC_OUT  = 3
OPC_OUTI = 4
OPC_IN   = 5
OPC_JMP  = 6
OPC_JNC  = 7
OPC_JZ   = 8
OPC_AND  = 9
OPC_OR   = 10
OPC_XOR  = 11
OPC_ADD  = 12
OPC_ADDI = 13
OPC_SUB  = 14
OPC_SUBI = 15

OPC_NAMES = {
    0:'NOP', 1:'MOV', 2:'MOVI', 3:'OUT', 4:'OUTI', 5:'IN',
    6:'JMP', 7:'JNC', 8:'JZ',
    9:'AND', 10:'OR', 11:'XOR',
    12:'ADD', 13:'ADDI', 14:'SUB', 15:'SUBI',
}


class TanukiCPU:
    ROM_SIZE = 16  # 4bit アドレス → 16 ワード

    def __init__(self, rom=None):
        self.rom = [0] * self.ROM_SIZE
        if rom:
            for i, v in enumerate(rom[:self.ROM_SIZE]):
                self.rom[i] = v & 0xFF
        self.reset()

    def reset(self):
        self.R = [0, 0, 0, 0]  # R0〜R3 (4bit)
        self.PC = 0             # プログラムカウンタ (4bit)
        self.C = 0              # キャリーフラグ
        self.Z = 0              # ゼロフラグ
        self.out_port = 0       # OUT ポート
        self.in_port = 0        # IN ポート（外部から設定）
        self.cycle = 0          # 実行命令数

    def load_rom(self, rom):
        for i, v in enumerate(rom[:self.ROM_SIZE]):
            self.rom[i] = v & 0xFF

    # ------------------------------------------------------------------
    # ALU: 組み合わせ回路
    # 返り値: (y[3:0], c, z)
    # 減算: 2の補数加算。キャリー=0 がボロー（a<b のとき C=0）
    # ------------------------------------------------------------------
    def _alu(self, op, a, b):
        a &= 0xF
        b &= 0xF
        if op == ALU_NOP:
            y, c = 0, 0
        elif op == ALU_PASSA:
            y, c = a, 0
        elif op == ALU_AND:
            y, c = a & b, 0
        elif op == ALU_OR:
            y, c = a | b, 0
        elif op == ALU_XOR:
            y, c = a ^ b, 0
        elif op == ALU_ADD:
            r = a + b
            y, c = r & 0xF, (r >> 4) & 1
        elif op == ALU_SUB:   # a - b
            r = a + ((~b) & 0xF) + 1
            y, c = r & 0xF, (r >> 4) & 1
        elif op == ALU_SUBR:  # b - a
            r = b + ((~a) & 0xF) + 1
            y, c = r & 0xF, (r >> 4) & 1
        else:
            y, c = 0, 0
        z = 1 if (y & 0xF) == 0 else 0
        return y & 0xF, c, z

    # ------------------------------------------------------------------
    # MUX 読み出し
    # ------------------------------------------------------------------
    def _read_mux(self, sel, opr):
        if sel <= 3:
            return self.R[sel]
        if sel == MUX_OPR:
            return opr & 0xF
        if sel == MUX_IN:
            return self.in_port & 0xF
        return 0

    # ------------------------------------------------------------------
    # 1命令実行
    # 返り値: (opc, opr) — トレース用
    # ------------------------------------------------------------------
    def step(self):
        instr = self.rom[self.PC & 0xF]
        opc = instr & 0xF          # D[3:0] = OPC
        opr = (instr >> 4) & 0xF  # D[7:4] = OPR
        ri = (opr >> 2) & 3   # レジスタ-レジスタ命令の宛先レジスタ番号
        rj = opr & 3           # レジスタ-レジスタ命令のソースレジスタ番号

        pc_next = (self.PC + 1) & 0xF
        wr_sel = None
        rd_a   = None
        rd_b   = None
        we     = False
        alu_op = ALU_NOP
        upd_c  = False
        upd_z  = False

        if opc == OPC_NOP:    # NOP: /WE=1, 何もしない
            pass
        elif opc == OPC_MOV:  # MOV Ri, Rj: Ri ← Rj
            wr_sel, rd_a, we, alu_op = ri, rj, True, ALU_PASSA
        elif opc == OPC_MOVI: # MOVI R0, Im: R0 ← Im
            wr_sel, rd_a, we, alu_op = 0, MUX_OPR, True, ALU_PASSA
        elif opc == OPC_OUT:  # OUT Ri: OUTPORT ← Ri
            wr_sel, rd_a, we, alu_op = MUX_OUT, ri, True, ALU_PASSA
        elif opc == OPC_OUTI: # OUTI Im: OUTPORT ← Im
            wr_sel, rd_a, we, alu_op = MUX_OUT, MUX_OPR, True, ALU_PASSA
        elif opc == OPC_IN:   # IN Ri: Ri ← INPORT
            wr_sel, rd_a, we, alu_op, upd_z = ri, MUX_IN, True, ALU_PASSA, True
        elif opc == OPC_JMP:  # JMP Addr: PC ← Addr
            wr_sel, rd_a, we, alu_op = MUX_PC, MUX_OPR, True, ALU_PASSA
        elif opc == OPC_JNC:  # JNC Addr: C==0 なら PC ← Addr
            if self.C == 0:
                wr_sel, rd_a, we, alu_op = MUX_PC, MUX_OPR, True, ALU_PASSA
        elif opc == OPC_JZ:   # JZ Addr: Z==1 なら PC ← Addr
            if self.Z == 1:
                wr_sel, rd_a, we, alu_op = MUX_PC, MUX_OPR, True, ALU_PASSA
        elif opc == OPC_AND:  # AND Ri, Rj: Ri ← Ri & Rj
            wr_sel, rd_a, rd_b, we, alu_op, upd_z = ri, ri, rj, True, ALU_AND, True
        elif opc == OPC_OR:   # OR Ri, Rj: Ri ← Ri | Rj
            wr_sel, rd_a, rd_b, we, alu_op, upd_z = ri, ri, rj, True, ALU_OR, True
        elif opc == OPC_XOR:  # XOR Ri, Rj: Ri ← Ri ^ Rj
            wr_sel, rd_a, rd_b, we, alu_op, upd_z = ri, ri, rj, True, ALU_XOR, True
        elif opc == OPC_ADD:  # ADD Ri, Rj: Ri ← Ri + Rj
            wr_sel, rd_a, rd_b, we, alu_op = ri, ri, rj, True, ALU_ADD
            upd_c = upd_z = True
        elif opc == OPC_ADDI: # ADDI R0, Im: R0 ← R0 + Im
            wr_sel, rd_a, rd_b, we, alu_op = 0, MUX_OPR, 0, True, ALU_ADD
            upd_c = upd_z = True
        elif opc == OPC_SUB:  # SUB Ri, Rj: Ri ← Ri - Rj
            wr_sel, rd_a, rd_b, we, alu_op = ri, ri, rj, True, ALU_SUB
            upd_c = upd_z = True
        elif opc == OPC_SUBI: # SUBI R0, Im: R0 ← R0 - Im (SUBR: y=b-a, a=Im, b=R0)
            wr_sel, rd_a, rd_b, we, alu_op = 0, MUX_OPR, 0, True, ALU_SUBR
            upd_c = upd_z = True

        a = self._read_mux(rd_a, opr) if rd_a is not None else 0
        b = self._read_mux(rd_b, opr) if rd_b is not None else 0
        y, c_new, z_new = self._alu(alu_op, a, b)

        if we and wr_sel is not None:
            if wr_sel <= 3:
                self.R[wr_sel] = y
            elif wr_sel == MUX_PC:
                pc_next = y
            elif wr_sel == MUX_OUT:
                self.out_port = y

        if upd_c:
            self.C = c_new
        if upd_z:
            self.Z = z_new

        self.PC = pc_next
        self.cycle += 1
        return opc, opr

    def state(self):
        return {
            'cycle': self.cycle,
            'PC':    self.PC,
            'R':     list(self.R),
            'C':     self.C,
            'Z':     self.Z,
            'OUT':   self.out_port,
            'IN':    self.in_port,
        }
