"""tanuki 4bit CPU インタラクティブシミュレータ

使い方:
  python sim.py                        デフォルト (counter)
  python sim.py --prog counter         プログラム指定
  python sim.py --prog adder
  python sim.py --step                 1ステップ実行モード
  python sim.py --cycles 64            実行サイクル数
  python sim.py --in 5                 IN ポートの初期値
"""

import argparse
import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from cpu import TanukiCPU
from asm import disasm, dump_rom


# ---------- 表示ヘルパー ----------

def fmt_state(s):
    r = s['R']
    return (
        f"PC:{s['PC']:X}  "
        f"R0:{r[0]:X} R1:{r[1]:X} R2:{r[2]:X} R3:{r[3]:X}  "
        f"C:{s['C']} Z:{s['Z']}  "
        f"OUT:{s['OUT']:X}  IN:{s['IN']:X}"
    )

def fmt_trace(cycle, pc, instr_byte, s_after):
    r = s_after['R']
    return (
        f"[{cycle:4d}] PC:{pc:X}  {disasm(instr_byte):<18s}  "
        f"R0:{r[0]:X} R1:{r[1]:X} R2:{r[2]:X} R3:{r[3]:X}  "
        f"C:{s_after['C']} Z:{s_after['Z']}  OUT:{s_after['OUT']:X}"
    )


# ---------- 実行モード ----------

def run_trace(cpu, cycles):
    """トレース出力しながら実行"""
    print(f"\n{'Cycle':>5}  {'PC':>2}  {'Instruction':<18}  "
          f"{'R0':>2} {'R1':>2} {'R2':>2} {'R3':>2}  C Z  OUT")
    print("-" * 70)
    for _ in range(cycles):
        pc = cpu.PC
        instr_byte = cpu.rom[pc & 0xF]
        cpu.step()
        s = cpu.state()
        print(fmt_trace(s['cycle'], pc, instr_byte, s))

def run_step(cpu, cycles):
    """1ステップずつ Enter で進む"""
    print("\n[ステップ実行] Enter で次へ、q+Enter で終了\n")
    for _ in range(cycles):
        pc = cpu.PC
        instr_byte = cpu.rom[pc & 0xF]
        print(f"  次の命令: PC:{pc:X}  {disasm(instr_byte)}")
        key = input("  > ").strip().lower()
        if key == 'q':
            break
        cpu.step()
        s = cpu.state()
        print(f"  {fmt_state(s)}\n")


# ---------- メイン ----------

def main():
    parser = argparse.ArgumentParser(description='tanuki 4bit CPU simulator')
    parser.add_argument('--prog',   default='counter',
                        help='プログラム名 (counter / adder / ...)')
    parser.add_argument('--step',   action='store_true',
                        help='1ステップ実行モード')
    parser.add_argument('--cycles', type=int, default=32,
                        help='実行サイクル数 (デフォルト: 32)')
    parser.add_argument('--in',     type=lambda x: int(x, 0), default=0,
                        dest='in_val', metavar='VAL',
                        help='IN ポートの初期値 (0〜15)')
    args = parser.parse_args()

    # プログラムロード
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

    # CPU 初期化
    cpu = TanukiCPU(rom)
    cpu.in_port = args.in_val & 0xF

    print(f"\n=== tanuki 4bit CPU シミュレータ ===")
    print(f"プログラム : {args.prog}")
    if desc:
        print(f"説明       : {desc}")
    print(f"IN ポート  : {cpu.in_port}")
    print(f"実行サイクル: {args.cycles}")

    print("\n--- ROM ダンプ ---")
    dump_rom(rom)

    print(f"\n--- 初期状態 ---")
    print(f"  {fmt_state(cpu.state())}")

    print(f"\n--- 実行 ---")
    if args.step:
        run_step(cpu, args.cycles)
    else:
        run_trace(cpu, args.cycles)

    print(f"\n--- 最終状態 ---")
    print(f"  {fmt_state(cpu.state())}")


if __name__ == '__main__':
    main()
