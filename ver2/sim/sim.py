"""TB-04 ver2 命令単位シミュレータ CLI ランナー

サンプルプログラムを実行しトレース表示する。論理検証は test_cpu.py。

実行:
    python sim.py                 # counter デモ
    python sim.py --prog led_flow # 流れるLED（OUTIパターン）
    python sim.py --trace          # 各命令のトレース表示
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpu import TB04CPU
from asm import disasm, dump_rom
from programs import PROGRAMS


def prog_countdown():
    """5→0 カウントダウン（JNZループ・0でHALT）。フェーズ検証の定番。"""
    from asm import Asm
    p = Asm()
    p.MOVI(0, 5)
    p.label('loop')
    p.OUT(0, 0)
    p.SEC(); p.SUBI(0, 1)
    p.JNZ('loop')
    p.HALT()
    return p, 'カウントダウン 5→0（JNZ ループ・0で HALT）'


PROGRAMS = dict(PROGRAMS, countdown=prog_countdown)


def fmt(info):
    r = info['R']
    return (f"[{info['cycle']:3d}] {disasm(info['byte1'], info['byte2']):<16s} "
            f"PC:{info['PC']:#04x} SP:{info['SP']} "
            f"R0:{r[0]:X} R1:{r[1]:X} R2:{r[2]:X} R3:{r[3]:X} "
            f"C:{info['C']} Z:{info['Z']} OUT:{info['OUT']}")


def main():
    ap = argparse.ArgumentParser(description='TB-04 ver2 命令単位シミュレータ')
    ap.add_argument('--prog', default='counter', choices=PROGRAMS.keys())
    ap.add_argument('--steps', type=int, default=40, help='実行命令数（HALTで停止）')
    ap.add_argument('--trace', action='store_true', help='各命令をトレース表示')
    ap.add_argument('--in', dest='in0', type=lambda x: int(x, 0), default=0,
                    metavar='VAL', help='IN ポート0 の初期値（counter/led_flow/life_ca）')
    ap.add_argument('--outseq', action='store_true', help='OUT書込列だけ表示')
    args = ap.parse_args()

    builder, desc = PROGRAMS[args.prog]()
    rom = builder.assemble()
    cpu = TB04CPU(rom)
    cpu.in_ports[0] = args.in0 & 0xF

    print(f'=== TB-04 ver2 命令単位シミュレータ ===')
    print(f'プログラム: {args.prog} — {desc}')
    print('--- ROM ダンプ ---')
    dump_rom(rom)
    print(f'--- 実行（最大{args.steps}命令）---')

    log = cpu.run(max_instr=args.steps, trace=True)
    if args.trace:
        for info in log:
            print(fmt(info))
    if args.outseq:
        seq = ' '.join(f'{v:X}' for _, p, v in cpu.out_log)
        print(f'--- OUT列（ポート0）---\n  {seq}')
    s = cpu.state()
    print('--- 最終状態 ---')
    print(f"  cycle:{s['cycle']} PC:{s['PC']:#04x} SP:{s['SP']} "
          f"R:{[f'{x:X}' for x in s['R']]} C:{s['C']} Z:{s['Z']} "
          f"OUT:{s['OUT']}" + ('  [HALT]' if cpu.halted else ''))


if __name__ == '__main__':
    main()
