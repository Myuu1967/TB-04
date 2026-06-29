"""tanuki 4bit CPU フェーズ精密シミュレータ（4フェーズ・クロック単位）

cpu.py の命令単位モデル（1 step = 1命令）とは別物。
こちらは 1 step = 1フェーズ（1クロック）で進み、実機の4フェーズ構成を再現する。
既存の cpu.py / sim.py / asm.py には手を入れず、定数・逆アセンブラは再利用する。

フェーズ構成（2026-06-30 の回路改修を反映）:
  FCH : PC番地のROMから命令をフェッチし命令レジスタ(IR)へ
  DEC : デコード結果をラッチ。PC をインクリメント（PC ← PC+1）
  EXE : ALU実行、レジスタ/OUTへ書き込み(WE)、ジャンプ時はPCへアドレスをロード、
        フラグ C/Z をラッチ
  WB  : 何もしない（リセット時のから打ち＝プライミング用の空フェーズ）

通常命令は DEC で PC が +1 され、ジャンプ命令は EXE でその PC をジャンプ先で
上書きするため、ディレイスロットなしで 4クロック/命令で動作する。
リセット直後は WB（空打ち）から始動し、最初の FCH を確実に成立させる。
"""

import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpu import (
    ALU_NOP, ALU_PASSA, ALU_AND, ALU_OR, ALU_XOR, ALU_ADD, ALU_SUB, ALU_SUBR,
    MUX_OPR, MUX_IN, MUX_PC, MUX_OUT,
    OPC_NOP, OPC_MOV, OPC_MOVI, OPC_OUT, OPC_OUTI, OPC_IN,
    OPC_JMP, OPC_JNC, OPC_JZ, OPC_AND, OPC_OR, OPC_XOR,
    OPC_ADD, OPC_ADDI, OPC_SUB, OPC_SUBI,
)
from asm import disasm, dump_rom

PHASES = ['FCH', 'DEC', 'EXE', 'WB']


class TanukiCPUPhase:
    """フェーズ（クロック）単位で進む tanuki CPU モデル。"""

    ROM_SIZE = 16  # 4bit アドレス → 16 ワード

    def __init__(self, rom=None):
        self.rom = [0] * self.ROM_SIZE
        if rom:
            self.load_rom(rom)
        self.reset()

    def load_rom(self, rom):
        for i, v in enumerate(rom[:self.ROM_SIZE]):
            self.rom[i] = v & 0xFF

    def reset(self):
        self.R = [0, 0, 0, 0]   # R0〜R3 (4bit)
        self.PC = 0             # プログラムカウンタ (4bit)
        self.C = 0              # キャリーフラグ
        self.Z = 0              # ゼロフラグ
        self.out_port = 0       # OUT ポート
        self.in_port = 0        # IN ポート（外部から設定）
        self.IR = 0             # 命令レジスタ（FCH でラッチ）
        self.dec = None         # デコード結果ラッチ（DEC でラッチ）
        self.phase_idx = 3      # WB から始動（プライミング）
        self.clock = 0          # 経過クロック数
        self.instr = 0          # 完了命令数（EXE 通過でカウント）

    # ------------------------------------------------------------------
    # ALU（組み合わせ回路）— cpu.py._alu と同一ロジック
    # 返り値: (y[3:0], c, z)。減算は2の補数加算、C=0 がボロー
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
        elif op == ALU_SUB:    # a - b
            r = a + ((~b) & 0xF) + 1
            y, c = r & 0xF, (r >> 4) & 1
        elif op == ALU_SUBR:   # b - a
            r = b + ((~a) & 0xF) + 1
            y, c = r & 0xF, (r >> 4) & 1
        else:
            y, c = 0, 0
        z = 1 if (y & 0xF) == 0 else 0
        return y & 0xF, c, z

    def _read_mux(self, sel):
        if sel is None:
            return 0
        if sel <= 3:
            return self.R[sel]
        if sel == MUX_OPR:
            return self.dec['opr'] & 0xF
        if sel == MUX_IN:
            return self.in_port & 0xF
        return 0

    # ------------------------------------------------------------------
    # デコード: IR → 制御信号（cpu.py.step の割り当てと同一）
    # ジャンプ条件の判定は EXE フェーズで行うため jcond だけ持たせる
    # ------------------------------------------------------------------
    def _decode(self):
        instr = self.IR
        opc = instr & 0xF
        opr = (instr >> 4) & 0xF
        ri = (opr >> 2) & 3
        rj = opr & 3

        d = {
            'opc': opc, 'opr': opr,
            'wr_sel': None, 'rd_a': None, 'rd_b': None,
            'we': False, 'alu_op': ALU_NOP,
            'upd_c': False, 'upd_z': False,
            'jcond': None,   # None / 'always' / 'nc' / 'z'
        }

        if opc == OPC_NOP:      # NOP: /WE=1, 何もしない
            pass
        elif opc == OPC_MOV:    # MOV Ri, Rj: Ri ← Rj
            d.update(wr_sel=ri, rd_a=rj, we=True, alu_op=ALU_PASSA)
        elif opc == OPC_MOVI:   # MOVI R0, Im: R0 ← Im
            d.update(wr_sel=0, rd_a=MUX_OPR, we=True, alu_op=ALU_PASSA)
        elif opc == OPC_OUT:    # OUT Ri: OUTPORT ← Ri
            d.update(wr_sel=MUX_OUT, rd_a=ri, we=True, alu_op=ALU_PASSA)
        elif opc == OPC_OUTI:   # OUTI Im: OUTPORT ← Im
            d.update(wr_sel=MUX_OUT, rd_a=MUX_OPR, we=True, alu_op=ALU_PASSA)
        elif opc == OPC_IN:     # IN Ri: Ri ← INPORT
            d.update(wr_sel=ri, rd_a=MUX_IN, we=True, alu_op=ALU_PASSA, upd_z=True)
        elif opc == OPC_JMP:    # JMP Addr: PC ← Addr
            d.update(jcond='always')
        elif opc == OPC_JNC:    # JNC Addr: C==0 なら PC ← Addr
            d.update(jcond='nc')
        elif opc == OPC_JZ:     # JZ Addr: Z==1 なら PC ← Addr
            d.update(jcond='z')
        elif opc == OPC_AND:    # AND Ri, Rj: Ri ← Ri & Rj
            d.update(wr_sel=ri, rd_a=ri, rd_b=rj, we=True, alu_op=ALU_AND, upd_z=True)
        elif opc == OPC_OR:     # OR Ri, Rj: Ri ← Ri | Rj
            d.update(wr_sel=ri, rd_a=ri, rd_b=rj, we=True, alu_op=ALU_OR, upd_z=True)
        elif opc == OPC_XOR:    # XOR Ri, Rj: Ri ← Ri ^ Rj
            d.update(wr_sel=ri, rd_a=ri, rd_b=rj, we=True, alu_op=ALU_XOR, upd_z=True)
        elif opc == OPC_ADD:    # ADD Ri, Rj: Ri ← Ri + Rj
            d.update(wr_sel=ri, rd_a=ri, rd_b=rj, we=True, alu_op=ALU_ADD,
                     upd_c=True, upd_z=True)
        elif opc == OPC_ADDI:   # ADDI R0, Im: R0 ← R0 + Im
            d.update(wr_sel=0, rd_a=MUX_OPR, rd_b=0, we=True, alu_op=ALU_ADD,
                     upd_c=True, upd_z=True)
        elif opc == OPC_SUB:    # SUB Ri, Rj: Ri ← Ri - Rj
            d.update(wr_sel=ri, rd_a=ri, rd_b=rj, we=True, alu_op=ALU_SUB,
                     upd_c=True, upd_z=True)
        elif opc == OPC_SUBI:   # SUBI R0, Im: R0 ← R0 - Im (SUBR: y=b-a)
            d.update(wr_sel=0, rd_a=MUX_OPR, rd_b=0, we=True, alu_op=ALU_SUBR,
                     upd_c=True, upd_z=True)
        return d

    # ------------------------------------------------------------------
    # 各フェーズの処理
    # ------------------------------------------------------------------
    def _phase_fch(self):
        self.IR = self.rom[self.PC & 0xF]

    def _phase_dec(self):
        self.dec = self._decode()
        self.PC = (self.PC + 1) & 0xF   # PC インクリメントは DEC

    def _phase_exe(self):
        d = self.dec
        # ジャンプ条件判定（前命令の EXE で確定したフラグを参照）
        do_jump = (d['jcond'] == 'always'
                   or (d['jcond'] == 'nc' and self.C == 0)
                   or (d['jcond'] == 'z' and self.Z == 1))

        a = self._read_mux(d['rd_a'])
        b = self._read_mux(d['rd_b'])
        y, c_new, z_new = self._alu(d['alu_op'], a, b)

        # レジスタ / OUT 書き込み（WE）
        if d['we'] and d['wr_sel'] is not None:
            ws = d['wr_sel']
            if ws <= 3:
                self.R[ws] = y
            elif ws == MUX_OUT:
                self.out_port = y

        # ジャンプ: DEC で +1 した PC をジャンプ先で上書き
        # （実機は ALU で PASS_A(addr) を通し MUX_PC 経由で PC にロード）
        if do_jump:
            self.PC = d['opr'] & 0xF

        # フラグラッチ（実機は EXE で無条件ラッチ、ROM 側で NOP/PASS_A の
        # C/Z を 0 に吸収。ここでは命令単位モデルと同じ upd_c/upd_z で再現）
        if d['upd_c']:
            self.C = c_new
        if d['upd_z']:
            self.Z = z_new

    # ------------------------------------------------------------------
    # 1フェーズ（1クロック）実行。返り値はトレース用の状態スナップショット
    # ------------------------------------------------------------------
    def step_phase(self):
        phase = PHASES[self.phase_idx]
        if phase == 'FCH':
            self._phase_fch()
        elif phase == 'DEC':
            self._phase_dec()
        elif phase == 'EXE':
            self._phase_exe()
        # WB は何もしない

        info = {
            'clock': self.clock,
            'phase': phase,
            'PC': self.PC,
            'IR': self.IR,
            'R': list(self.R),
            'C': self.C,
            'Z': self.Z,
            'OUT': self.out_port,
            'IN': self.in_port,
            'instr': self.instr,
        }

        self.clock += 1
        if phase == 'EXE':
            self.instr += 1
        self.phase_idx = (self.phase_idx + 1) % 4
        return info

    def step_instr(self):
        """1命令（4フェーズ）分まとめて進める。EXE 直後の状態を返す。"""
        info = None
        target = self.instr + 1
        # 最大 4フェーズ進めて EXE を 1 回通す
        for _ in range(4):
            info = self.step_phase()
            if self.instr == target:
                break
        return info

    def state(self):
        return {
            'clock': self.clock,
            'phase': PHASES[self.phase_idx],
            'instr': self.instr,
            'PC': self.PC,
            'R': list(self.R),
            'C': self.C,
            'Z': self.Z,
            'OUT': self.out_port,
            'IN': self.in_port,
        }


# ---------- 表示ヘルパー ----------

def fmt_phase(info):
    r = info['R']
    # FCH 行にだけ、フェッチした命令の逆アセンブルを表示
    instr_str = disasm(info['IR']) if info['phase'] == 'FCH' else ''
    return (
        f"[{info['clock']:4d}] {info['phase']:3s}  PC:{info['PC']:X}  "
        f"{instr_str:<18s}  "
        f"R0:{r[0]:X} R1:{r[1]:X} R2:{r[2]:X} R3:{r[3]:X}  "
        f"C:{info['C']} Z:{info['Z']}  OUT:{info['OUT']:X}"
    )


def run_trace(cpu, clocks):
    print(f"\n{'Clk':>5}  Phs  {'PC':>2}  {'Instruction(FCH)':<18}  "
          f"{'R0':>2} {'R1':>2} {'R2':>2} {'R3':>2}  C Z  OUT")
    print("-" * 74)
    for _ in range(clocks):
        info = cpu.step_phase()
        line = fmt_phase(info)
        print(line)
        if info['phase'] == 'WB':   # 1命令(4クロック)の区切り
            print("  " + "-" * 60)


# ---------- メイン ----------

def main():
    parser = argparse.ArgumentParser(
        description='tanuki 4bit CPU フェーズ精密シミュレータ')
    parser.add_argument('--prog', default='counter',
                        help='プログラム名 (counter / adder / ...)')
    parser.add_argument('--clocks', type=int, default=32,
                        help='実行クロック数（4クロック=1命令、デフォルト: 32）')
    parser.add_argument('--in', type=lambda x: int(x, 0), default=0,
                        dest='in_val', metavar='VAL',
                        help='IN ポートの初期値 (0〜15)')
    args = parser.parse_args()

    prog_path = os.path.join(os.path.dirname(__file__), 'programs', f'{args.prog}.py')
    if not os.path.exists(prog_path):
        print(f"エラー: プログラム '{args.prog}' が見つかりません")
        print(f"  場所: {prog_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location('program', prog_path)
    prog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prog)

    rom = prog.ROM
    desc = getattr(prog, 'DESCRIPTION', '')

    cpu = TanukiCPUPhase(rom)
    cpu.in_port = args.in_val & 0xF

    print(f"\n=== tanuki 4bit CPU フェーズ精密シミュレータ ===")
    print(f"プログラム : {args.prog}")
    if desc:
        print(f"説明       : {desc}")
    print(f"IN ポート  : {cpu.in_port}")
    print(f"実行クロック: {args.clocks}（4クロック=1命令）")
    print(f"フェーズ   : FCH→DEC（PC+1）→EXE（演算・WE・分岐・フラグ）→WB（空）")

    print("\n--- ROM ダンプ ---")
    dump_rom(rom)

    print(f"\n--- 実行（リセット後は WB から始動）---")
    run_trace(cpu, args.clocks)

    s = cpu.state()
    print(f"\n--- 最終状態 ---")
    print(f"  clock:{s['clock']} instr:{s['instr']} 次phase:{s['phase']}  "
          f"PC:{s['PC']:X}  R0:{s['R'][0]:X} R1:{s['R'][1]:X} "
          f"R2:{s['R'][2]:X} R3:{s['R'][3]:X}  "
          f"C:{s['C']} Z:{s['Z']}  OUT:{s['OUT']:X}")


if __name__ == '__main__':
    main()
