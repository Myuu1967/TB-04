"""TB-04 ver2 フェーズ精密シミュレータ（4相・クロック単位）

`cpu.py` の命令単位モデル（1 step = 1命令）とは別に、1 step = 1フェーズ
（1クロック）で進み、固定2語命令の4相構成を再現する。命令の実行ロジックは
`cpu.py` の `_exec_*` を**そのまま再利用**（＝単一の真実。命令単位モデルと乖離しない）。
本モデルはフェーズ制御（2語フェッチ・PC++×2・EXE反映）だけを上に載せる。

フェーズ構成（ver2_sequence.csv・ドラフト§7/§9）:
  FCH1 : AB=PC → byte1 をラッチ（IR）、PC←PC+1
  FCH2 : AB=PC → byte2 をラッチ（オペランド）、PC←PC+1  （PC は命令先頭+2 になる）
  DCR  : デコード結果をラッチ（デコーダROM読出）。状態は変えない
  EXE  : ALU実行・レジスタ/メモリ書込(/WE,/WR)・分岐(PC_LOAD&SEL_PC)・
         フラグラッチ(C_WE,Z_WE)・スタック増減。CALL は戻り番地(=PC=先頭+2)を退避

リセット：PC=0/SP=7/C=0/Z=0/位相=FCH1。ver1 のような WB プライミングは不要
（4相の初回 FCH1 で addr0 を読む。ドラフト§8/§12-6）。

モデル上の注記:
  書込・スタック増減・分岐・フラグは本モデルでは**すべて EXE で反映**する
  （命令単位の _exec_* を EXE で1回呼ぶため）。sequence.csv では POP/RET の
  SP++ は DCR 相当だが、**最終状態は命令単位モデルと同一**（cross-check で検証）。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpu import TB04CPU, PFX_E, PFX_F
from asm import disasm

PHASES = ['FCH1', 'FCH2', 'DCR', 'EXE']


class TB04CPUPhase:
    """フェーズ（クロック）単位で進む TB-04 ver2 モデル。状態は内部の TB04CPU が保持。"""

    def __init__(self, rom=None, multi_nibble_z=False):
        self.core = TB04CPU(rom, multi_nibble_z)
        self.reset()

    def load_rom(self, rom):
        self.core.load_rom(rom)

    def reset(self):
        self.core.reset()
        self.phase_idx = 0     # FCH1 起点（プライミング不要）
        self.clock = 0
        self.instr = 0         # 完了命令数（EXE 通過でカウント）
        self.instr_addr = 0    # 現在命令の先頭番地（FCH1 で確定）
        self.byte1 = 0
        self.byte2 = 0
        self.mnem = ''

    # ------------------------------------------------------------------
    def _exe(self):
        """EXE 相：cpu.py の _exec_* を再利用して命令効果を反映。"""
        c = self.core
        b1, b2 = self.byte1, self.byte2
        hi = (b1 >> 4) & 0xF
        ri_b2 = (b2 >> 4) & 0x7
        rj_b2 = b2 & 0x7
        ri_b1 = b1 & 0x7
        im4_b1 = b1 & 0xF
        im4_b2 = b2 & 0xF
        addr8 = b2 & 0xFF
        port_io = b2 & 0x3
        port_outi = (b2 >> 4) & 0x3
        next_pc = c.PC & 0xFF   # FCH2 後の PC ＝ 命令先頭+2 ＝ 戻り/次番地

        if hi == PFX_E:
            self.mnem = c._exec_E(b1 & 0xF, b2, ri_b2, rj_b2, addr8,
                                  im4_b2, port_io, port_outi, next_pc)
        elif hi == PFX_F:
            self.mnem = c._exec_F(b1 & 0xF, ri_b2, rj_b2, im4_b2)
            c.PC = next_pc
        else:
            self.mnem = c._exec_single(hi, ri_b1, ri_b2, rj_b2, im4_b1, addr8)
            c.PC = next_pc
        c.cycle += 1

    def step_phase(self):
        c = self.core
        phase = PHASES[self.phase_idx]
        if phase == 'FCH1':
            self.instr_addr = c.PC & 0xFF
            self.byte1 = c.mem[c.PC & 0xFF] & 0xFF
            c.PC = (c.PC + 1) & 0xFF
            self.mnem = ''
        elif phase == 'FCH2':
            self.byte2 = c.mem[c.PC & 0xFF] & 0xFF
            c.PC = (c.PC + 1) & 0xFF
        elif phase == 'DCR':
            self.mnem = disasm(self.byte1, self.byte2)   # デコード（表示用ラッチ）
        elif phase == 'EXE':
            self._exe()

        info = self._snapshot(phase)
        self.clock += 1
        if phase == 'EXE':
            self.instr += 1
        self.phase_idx = (self.phase_idx + 1) % 4
        return info

    def step_instr(self):
        """1命令（4相）分進める。EXE 直後のスナップショットを返す。"""
        info = None
        for _ in range(4):
            info = self.step_phase()
        return info

    def run(self, max_instr=1000, trace=False, stop_on_halt=True):
        log = []
        for _ in range(max_instr * 4):
            info = self.step_phase()
            if trace:
                log.append(info)
            if stop_on_halt and self.core.halted and PHASES[(self.phase_idx - 1) % 4] == 'EXE':
                break
        return log

    def _snapshot(self, phase):
        c = self.core
        return {
            'clock': self.clock, 'phase': phase, 'instr': self.instr,
            'addr': self.instr_addr, 'byte1': self.byte1, 'byte2': self.byte2,
            'mnem': self.mnem, 'PC': c.PC, 'SP': c.SP, 'R': list(c.R[:4]),
            'C': c.C, 'Z': c.Z, 'OUT': list(c.out_ports),
        }

    def state(self):
        s = self.core.state()
        s.update(clock=self.clock, phase=PHASES[self.phase_idx], instr=self.instr)
        return s


# ---------------------------------------------------------------------
def fmt(info):
    r = info['R']
    m = info['mnem'] if info['phase'] in ('DCR', 'EXE') else ''
    fetched = f"{info['byte1']:02X}{info['byte2']:02X}" if info['phase'] != 'FCH1' \
        else f"{info['byte1']:02X}.."
    return (f"[{info['clock']:4d}] {info['phase']:4s} @{info['addr']:#04x} {fetched:5s} "
            f"{m:<16s} PC:{info['PC']:#04x} SP:{info['SP']} "
            f"R0:{r[0]:X} R1:{r[1]:X} R2:{r[2]:X} R3:{r[3]:X} "
            f"C:{info['C']} Z:{info['Z']} OUT:{info['OUT'][0]}")


def main():
    sys.path.insert(0, os.path.dirname(__file__))
    from sim import PROGRAMS   # サンプルプログラムを共有
    ap = argparse.ArgumentParser(description='TB-04 ver2 フェーズ精密シミュレータ')
    ap.add_argument('--prog', default='countdown', choices=PROGRAMS.keys())
    ap.add_argument('--instr', type=int, default=12, help='実行命令数（4クロック=1命令）')
    args = ap.parse_args()

    builder, desc = PROGRAMS[args.prog]()
    cpu = TB04CPUPhase(builder.assemble())
    print(f'=== TB-04 ver2 フェーズ精密シミュレータ ===')
    print(f'プログラム: {args.prog} — {desc}')
    print(f'相: FCH1(byte1,PC++)→FCH2(byte2,PC++)→DCR→EXE（4クロック=1命令）\n')
    log = cpu.run(max_instr=args.instr, trace=True)
    for info in log:
        print(fmt(info))
        if info['phase'] == 'EXE':
            print('  ' + '-' * 60)
    s = cpu.state()
    print(f"\n最終: clock:{s['clock']} instr:{s['instr']} PC:{s['PC']:#04x} SP:{s['SP']} "
          f"R:{[f'{x:X}' for x in s['R']]} C:{s['C']} Z:{s['Z']} OUT:{s['OUT']}"
          + ('  [HALT]' if cpu.core.halted else ''))


if __name__ == '__main__':
    main()
