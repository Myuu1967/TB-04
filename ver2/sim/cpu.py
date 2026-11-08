"""TB-04 ver2（データ4bit・アドレス8bit）命令単位シミュレータ

ver1 sim/cpu.py の後継。1 step = 1命令を最後まで実行する命令単位モデルで、
クロック/フェーズ（FCH1/FCH2/DCR/EXE）はモデル化しない（論理検証用）。
フェーズ精密モデル（cpu_phase.py 相当）は別途。

仕様:
  命令表・ALU表は ver2/README.md、デコーダの真理値表は ver2/ver2_decoder_truthtable.csv。
  sim/・tools/ のコメントにある「ドラフト§n」は、非公開の設計メモの節番号。
本モデルは仕様に忠実に従う（信号・命令・ALUcode の定義は変更しない）。

主な ver2 拡張:
  - 8bit アドレス空間（256語）・単一8bitメモリバス（ROM/RAM/スタック/I-O）
  - 固定2語命令（byte1=opcode プレフィックス / byte2=オペランド）
  - E系(1110)/F系(1111) プレフィックス、単独ニブル(0-5)
  - スタック（CALL/RET/PUSH/POP、SP 3bit・飽和ガード）
  - フラグ保持（per-flag WE。分岐等ではC/Zを保持）
  - Cin=C_prev（ADD/SUB は ADC/SBC）、CLC/SEC で Cin 初期化
  - メモリマップド I/O（IN 0xF8-0xFB / OUT 0xFC-0xFF）

Zフラグ（2026-07-10 案A確定）:
  - **ver2 は Zin を持たない**＝`Z_out=(y==0)`（単精度・ver1同様）。ドラフト§1/§12-2。
  - `multi_nibble_z=True` は **ver3プレビュー**（多倍長ゼロ連鎖 Zin=Z_prev）。ver2仕様
    ではない。ver3では Zin 源を `chain?Z_prev:1` で切替（デコーダROM出力に吸収）。
  - レジスタは R0-R7 の8個（2026-07-02にver1のR0-R3から拡張）。レジスタ番地フィールドは
    3bit（byte2[6:4]＝Ri / byte2[2:0]＝Rj / LD・STのみ byte1[2:0]＝Ri）。回路も
    74HC161×8（RS00=R0-R3 / RS01=R4-R7）で8本を実装。
"""

# ---- ALU 演算コード（ドラフト§3 / 真理値表 AluCode 列。定義は変更しない）----
ALU_NOP    = 0   # y = 0
ALU_PASS_A = 1   # y = a
ALU_PASS_B = 2   # y = b
ALU_AND    = 3   # y = a & b
ALU_OR     = 4   # y = a | b
ALU_XOR    = 5   # y = a ^ b
ALU_NOT    = 6   # y = ~a
ALU_SHL    = 7   # y = {a[2:0],0},      Cout = a[3]
ALU_SHR    = 8   # y = {0,a[3:1]},      Cout = a[0]
ALU_ROL    = 9   # y = {a[2:0],a[3]}    （フラグ保持）
ALU_ROR    = 10  # y = {a[0],a[3:1]}    （フラグ保持）
ALU_ADD    = 11  # y = a + b + Cin
ALU_SUB    = 12  # y = a + ~b + Cin = a - b - 1 + Cin
ALU_SUBR   = 13  # 予約（旧 b-a・未使用）
ALU_CLC    = 14  # Cout = 0（レジスタ非書込）
ALU_SEC    = 15  # Cout = 1（レジスタ非書込）

# ---- 命令グループ ----
PFX_E = 0xE   # byte1 上位ニブル = 1110
PFX_F = 0xF   # byte1 上位ニブル = 1111

# ---- メモリマップ（ドラフト§4）----
ROM_END   = 0xBF   # 0x00-0xBF ROM（プログラム）
RAM_END   = 0xEF   # 0xC0-0xEF RAM（データ）
STACK_BASE = 0xF0  # 0xF0-0xF7 スタック（SP 3bit で 0xF0|SP）
IN_BASE   = 0xF8   # 0xF8-0xFB INPORT（4ポート）
OUT_BASE  = 0xFC   # 0xFC-0xFF OUTPORT（4ポート）


def alu(op, a, b, cin):
    """ALU 組み合わせ回路（純粋関数）。返り値 (y[3:0], cout)。

    ALU ROM 生成ツール（tools/gen_alu_rom.py）と本体が同一ロジックを共有する
    ための単一の真実。Z 出力は ROM 側で `(y==0)`（案A・ver2 は Zin なし）。
    """
    a &= 0xF
    b &= 0xF
    cin &= 1
    if op == ALU_NOP:
        y, cout = 0, 0
    elif op == ALU_PASS_A:
        y, cout = a, 0
    elif op == ALU_PASS_B:
        y, cout = b, 0
    elif op == ALU_AND:
        y, cout = a & b, 0
    elif op == ALU_OR:
        y, cout = a | b, 0
    elif op == ALU_XOR:
        y, cout = a ^ b, 0
    elif op == ALU_NOT:
        y, cout = (~a) & 0xF, 0
    elif op == ALU_SHL:
        y, cout = (a << 1) & 0xF, (a >> 3) & 1
    elif op == ALU_SHR:
        y, cout = (a >> 1) & 0xF, a & 1
    elif op == ALU_ROL:
        y, cout = ((a << 1) | (a >> 3)) & 0xF, 0   # フラグ保持
    elif op == ALU_ROR:
        y, cout = ((a >> 1) | (a << 3)) & 0xF, 0   # フラグ保持
    elif op == ALU_ADD:
        r = a + b + cin
        y, cout = r & 0xF, (r >> 4) & 1
    elif op == ALU_SUB:
        r = a + ((~b) & 0xF) + cin   # a - b - 1 + Cin
        y, cout = r & 0xF, (r >> 4) & 1
    elif op == ALU_CLC:
        y, cout = 0, 0
    elif op == ALU_SEC:
        y, cout = 0, 1
    else:  # ALU_SUBR（予約・未使用）ほか
        y, cout = 0, 0
    return y & 0xF, cout


class TB04CPU:
    MEM_SIZE = 256   # 8bit アドレス
    NUM_REGS = 8     # R0-R7（3bitフィールド byte2[6:4] / byte2[2:0] をフルに使う）

    def __init__(self, rom=None, multi_nibble_z=False):
        self.mem = [0] * self.MEM_SIZE
        self.multi_nibble_z = multi_nibble_z
        if rom is not None:
            self.load_rom(rom)
        self.reset()

    def load_rom(self, rom):
        """プログラム（バイト列）を 0 番地からロード。"""
        for i, v in enumerate(rom[:self.MEM_SIZE]):
            self.mem[i] = v & 0xFF

    def reset(self):
        self.R = [0] * self.NUM_REGS   # R0-R7
        self.PC = 0                    # 8bit
        self.SP = 7                    # 3bit、リセットで7（空）。物理番地=0xF0|SP
        self.C = 0
        self.Z = 0
        self.in_ports = [0, 0, 0, 0]   # IN[0..3]（外部から設定）
        self.out_ports = [0, 0, 0, 0]  # OUT[0..3]
        self.cycle = 0                 # 実行命令数
        self.halted = False            # HALT（自己JMP）検出用
        self.last_out = None           # 直近に書いた (port, value)
        self.out_log = []              # OUT書込履歴 [(cycle, port, value), ...]

    # ------------------------------------------------------------------
    # ALU（組み合わせ回路）。返り値 (y[3:0], cout)
    # ------------------------------------------------------------------
    def _alu(self, op, a, b, cin):
        return alu(op, a, b, cin)   # 単一の真実（モジュール関数）へ委譲

    def _zout(self, y):
        """Z_out = (y==0) & Zin。単精度は Zin=1、多倍長は Zin=Z_prev。"""
        z_raw = 1 if (y & 0xF) == 0 else 0
        if self.multi_nibble_z:
            return z_raw & self.Z
        return z_raw

    # ------------------------------------------------------------------
    # メモリアクセス（I/O ルーティング込み）
    # ------------------------------------------------------------------
    def _mem_read(self, addr):
        addr &= 0xFF
        if IN_BASE <= addr <= IN_BASE + 3:
            return self.in_ports[addr - IN_BASE] & 0xF
        if OUT_BASE <= addr <= OUT_BASE + 3:
            return self.out_ports[addr - OUT_BASE] & 0xF
        return self.mem[addr] & 0xFF

    def _mem_write(self, addr, val):
        addr &= 0xFF
        if OUT_BASE <= addr <= OUT_BASE + 3:
            p = addr - OUT_BASE
            self.out_ports[p] = val & 0xF
            self.last_out = (p, val & 0xF)
            self.out_log.append((self.cycle, p, val & 0xF))
            return
        if IN_BASE <= addr <= IN_BASE + 3:
            return  # INポートへの書込は無効
        if addr <= ROM_END:
            return  # ROM領域は書込不可（無視）
        self.mem[addr] = val & 0xFF

    def _stack_addr(self):
        return STACK_BASE | (self.SP & 0x7)

    # ------------------------------------------------------------------
    # 1命令実行。返り値: トレース用 dict
    # ------------------------------------------------------------------
    def step(self):
        pc = self.PC & 0xFF
        byte1 = self.mem[pc] & 0xFF
        byte2 = self.mem[(pc + 1) & 0xFF] & 0xFF
        next_pc = (pc + 2) & 0xFF

        hi = (byte1 >> 4) & 0xF
        # オペランド抽出（ドラフト§5）
        ri_b2 = (byte2 >> 4) & 0x7   # byte2[6:4]
        rj_b2 = byte2 & 0x7          # byte2[2:0]
        ri_b1 = byte1 & 0x7          # byte1[2:0]（LD/ST）
        im4_b1 = byte1 & 0xF         # byte1[3:0]（MOVI/STI）
        im4_b2 = byte2 & 0xF         # byte2[3:0]（ADDI/SUBI/OUTI）
        addr8 = byte2 & 0xFF         # 分岐/CALL/LD/ST の8bitアドレス
        port_io = byte2 & 0x3        # IN/OUT: byte2[1:0]
        port_outi = (byte2 >> 4) & 0x3  # OUTI: byte2[5:4]

        mnem = None
        if hi == PFX_E:
            mnem = self._exec_E(byte1 & 0xF, byte2, ri_b2, rj_b2,
                                addr8, im4_b2, port_io, port_outi, next_pc)
        elif hi == PFX_F:
            mnem = self._exec_F(byte1 & 0xF, ri_b2, rj_b2, im4_b2)
            self.PC = next_pc
        else:
            mnem = self._exec_single(hi, ri_b1, ri_b2, rj_b2, im4_b1, addr8)
            self.PC = next_pc

        self.cycle += 1
        return {'mnem': mnem, 'byte1': byte1, 'byte2': byte2, **self.state()}

    # ---- 単独ニブル群（NOP/MOV/MOVI/LD/ST/STI）----
    def _exec_single(self, opc, ri_b1, ri_b2, rj_b2, im4_b1, addr8):
        if opc == 0x0:      # NOP
            return 'NOP'
        if opc == 0x1:      # MOV Ri,Rj : Ri←Rj (PASS_B, a=Ri b=Rj)
            y, _ = self._alu(ALU_PASS_B, self.R[ri_b2], self.R[rj_b2], self.C)
            self.R[ri_b2] = y
            return f'MOV R{ri_b2},R{rj_b2}'
        if opc == 0x2:      # MOVI Ri,Im4 : Ri←Im4 (PASS_A, a=Im4 byte1[3:0], Ri byte2[6:4])
            y, _ = self._alu(ALU_PASS_A, im4_b1, 0, self.C)
            self.R[ri_b2] = y
            return f'MOVI R{ri_b2},{im4_b1}'
        if opc == 0x3:      # LD Ri,[Addr] : Ri←MEM[Addr] (PASS_B, b=MEM, Ri byte1[2:0])
            m = self._mem_read(addr8)
            y, _ = self._alu(ALU_PASS_B, 0, m, self.C)
            self.R[ri_b1] = y
            return f'LD R{ri_b1},[{addr8:#04x}]'
        if opc == 0x4:      # ST [Addr],Ri : MEM[Addr]←Ri (PASS_A, a=Ri byte1[2:0])
            y, _ = self._alu(ALU_PASS_A, self.R[ri_b1], 0, self.C)
            self._mem_write(addr8, y)
            return f'ST [{addr8:#04x}],R{ri_b1}'
        if opc == 0x5:      # STI [Addr],Im4 : MEM[Addr]←Im4 (PASS_A, a=Im4 byte1[3:0])
            y, _ = self._alu(ALU_PASS_A, im4_b1, 0, self.C)
            self._mem_write(addr8, y)
            return f'STI [{addr8:#04x}],{im4_b1}'
        return f'?single({opc:#x})'   # 0x6/0x7/0x8 予約

    # ---- E系（非ALU：分岐/スタック/I-O）----
    def _exec_E(self, sub, byte2, ri_b2, rj_b2, addr8, im4_b2, port_io, port_outi, next_pc):
        if sub == 0x0:      # JMP Addr
            if addr8 == (next_pc - 2) & 0xFF:   # 自己番地へのJMP＝HALT（擬似命令）
                self.halted = True
            self.PC = addr8
            return f'JMP {addr8:#04x}'
        if sub == 0x1:      # JC : C==1 で分岐
            taken = self.C == 1
            self.PC = addr8 if taken else next_pc
            return f'JC {addr8:#04x}'
        if sub == 0x2:      # JNC : C==0 で分岐
            taken = self.C == 0
            self.PC = addr8 if taken else next_pc
            return f'JNC {addr8:#04x}'
        if sub == 0x3:      # JZ : Z==1 で分岐
            taken = self.Z == 1
            self.PC = addr8 if taken else next_pc
            return f'JZ {addr8:#04x}'
        if sub == 0x4:      # JNZ : Z==0 で分岐
            taken = self.Z == 0
            self.PC = addr8 if taken else next_pc
            return f'JNZ {addr8:#04x}'
        if sub == 0x5:      # CALL Addr : MEM[SP]←PC(戻り番地); PC←Addr; SP-- (post-dec)
            self._mem_write(self._stack_addr(), next_pc)  # 8bit直結（ALU非経由）
            self.PC = addr8
            self._sp_dec()
            return f'CALL {addr8:#04x}'
        if sub == 0x6:      # RET : SP++ (pre-inc); PC←MEM[SP]
            self._sp_inc()
            self.PC = self._mem_read(self._stack_addr()) & 0xFF
            return 'RET'
        if sub == 0x7:      # 予約（旧HALT。擬似命令化でopcodeは予約）
            self.PC = next_pc
            return '?resv(E7)'
        if sub == 0x8:      # PUSH Ri : MEM[SP]←Ri; SP-- (post-dec)
            y, _ = self._alu(ALU_PASS_A, self.R[ri_b2], 0, self.C)
            self._mem_write(self._stack_addr(), y)
            self._sp_dec()
            self.PC = next_pc
            return f'PUSH R{ri_b2}'
        if sub == 0x9:      # POP Ri : SP++ (pre-inc); Ri←MEM[SP]
            self._sp_inc()
            m = self._mem_read(self._stack_addr())
            y, _ = self._alu(ALU_PASS_B, 0, m, self.C)
            self.R[ri_b2] = y
            self.PC = next_pc
            return f'POP R{ri_b2}'
        if sub == 0xA:      # IN Ri,port : Ri←IN[port]（Z更新）
            m = self._mem_read(IN_BASE | port_io)
            y, _ = self._alu(ALU_PASS_B, 0, m, self.C)
            self.R[ri_b2] = y
            self.Z = self._zout(y)
            self.PC = next_pc
            return f'IN R{ri_b2},{port_io}'
        if sub == 0xB:      # OUT port,Ri : OUT[port]←Ri
            y, _ = self._alu(ALU_PASS_A, self.R[ri_b2], 0, self.C)
            self._mem_write(OUT_BASE | port_io, y)
            self.PC = next_pc
            return f'OUT {port_io},R{ri_b2}'
        if sub == 0xC:      # OUTI port,Im4 : OUT[port]←Im4
            y, _ = self._alu(ALU_PASS_A, im4_b2, 0, self.C)
            self._mem_write(OUT_BASE | port_outi, y)
            self.PC = next_pc
            return f'OUTI {port_outi},{im4_b2}'
        self.PC = next_pc
        return f'?E({sub:#x})'

    # ---- F系（ALU演算）----
    def _exec_F(self, sub, ri_b2, rj_b2, im4_b2):
        a = self.R[ri_b2]
        rj = self.R[rj_b2]
        cin = self.C
        # (alu_op, b, dst_write, wr_c, wr_z, mnem)
        table = {
            0x0: (ALU_SUB, rj,      False, True,  True,  f'CP R{ri_b2},R{rj_b2}'),
            0x1: (ALU_AND, rj,      True,  False, True,  f'AND R{ri_b2},R{rj_b2}'),
            0x2: (ALU_OR,  rj,      True,  False, True,  f'OR R{ri_b2},R{rj_b2}'),
            0x3: (ALU_XOR, rj,      True,  False, True,  f'XOR R{ri_b2},R{rj_b2}'),
            0x4: (ALU_NOT, 0,       True,  False, True,  f'NOT R{ri_b2}'),
            0x5: (ALU_SHL, 0,       True,  True,  True,  f'SHL R{ri_b2}'),
            0x6: (ALU_SHR, 0,       True,  True,  True,  f'SHR R{ri_b2}'),
            0x7: (ALU_ROL, 0,       True,  False, False, f'ROL R{ri_b2}'),
            0x8: (ALU_ROR, 0,       True,  False, False, f'ROR R{ri_b2}'),
            0x9: (ALU_ADD, rj,      True,  True,  True,  f'ADD R{ri_b2},R{rj_b2}'),
            0xA: (ALU_ADD, im4_b2,  True,  True,  True,  f'ADDI R{ri_b2},{im4_b2}'),
            0xB: (ALU_SUB, rj,      True,  True,  True,  f'SUB R{ri_b2},R{rj_b2}'),
            0xC: (ALU_SUB, im4_b2,  True,  True,  True,  f'SUBI R{ri_b2},{im4_b2}'),
            0xD: (ALU_CLC, 0,       False, True,  False, 'CLC'),
            0xE: (ALU_SEC, 0,       False, True,  False, 'SEC'),
        }
        if sub not in table:
            return f'?F({sub:#x})'   # 0xF 予約
        alu_op, b, dst_write, wr_c, wr_z, mnem = table[sub]
        y, cout = self._alu(alu_op, a, b, cin)
        z_new = self._zout(y)
        if dst_write:
            self.R[ri_b2] = y
        if wr_c:
            self.C = cout
        if wr_z:
            self.Z = z_new
        return mnem

    def _sp_dec(self):
        if self.SP != 0:           # SP==0（満杯）で SP_CD 禁止（飽和ガード）
            self.SP = (self.SP - 1) & 0x7

    def _sp_inc(self):
        if self.SP != 7:           # SP==7（空）で SP_CU 禁止（飽和ガード）
            self.SP = (self.SP + 1) & 0x7

    # ------------------------------------------------------------------
    def run(self, max_instr=1000, trace=False, stop_on_halt=True):
        """最大 max_instr 命令実行。HALT（自己JMP）検出で停止。"""
        log = []
        for _ in range(max_instr):
            info = self.step()
            if trace:
                log.append(info)
            if stop_on_halt and self.halted:
                break
        return log

    def state(self):
        return {
            'cycle': self.cycle,
            'PC': self.PC,
            'SP': self.SP,
            'R': list(self.R[:4]),
            'C': self.C,
            'Z': self.Z,
            'IN': list(self.in_ports),
            'OUT': list(self.out_ports),
        }
