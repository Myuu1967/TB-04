#!/usr/bin/env python3
"""TB-04 ver2 ALU ROM データ生成ツール

ALU ROM（8192バイト＝13bit）の .bin/.hex を生成する。
演算ロジックはシミュレータ `ver2/sim/cpu.py` の `alu()` を**そのまま共有**する
（＝単一の真実。ROM と sim が乖離しない）。ドラフト§3/§1。

アドレス構成（13bit = 8192エントリ・案A＝Zin なし）:
  A0-A3  : a[3:0]     （ALU入力a）
  A4-A7  : b[3:0]     （ALU入力b）
  A8-A11 : alu_code   （0-15）
  A12    : Cin        （= C_prev。ADD/SUB のチェーンに使用）
  A13-A14: GND（未使用）
  → addr = a | (b<<4) | (alu_code<<8) | (Cin<<12)

出力バイト構成:
  D0-D3 : y[3:0]   （演算結果）
  D4    : Cout     （キャリー。減算は Cout=1⇔ボローなし）
  D5    : Z        （= (y==0)。案A・単精度。多倍長 Zin は ver3）
  D6-D7 : 0        （未使用）

※どの演算で C/Z を実際に採用するかはデコーダの /C_WE・/Z_WE が決める。
  ALU ROM は常に Cout と Z=(y==0) を出力する。
"""

import os
import sys

# sim/cpu.py の ALU を共有（単一の真実）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sim'))
from cpu import (  # noqa: E402
    alu,
    ALU_NOP, ALU_PASS_A, ALU_PASS_B, ALU_AND, ALU_OR, ALU_XOR, ALU_NOT,
    ALU_SHL, ALU_SHR, ALU_ROL, ALU_ROR, ALU_ADD, ALU_SUB, ALU_CLC, ALU_SEC,
)

ALU_NAMES = {
    ALU_NOP: 'NOP', ALU_PASS_A: 'PASS_A', ALU_PASS_B: 'PASS_B',
    ALU_AND: 'AND', ALU_OR: 'OR', ALU_XOR: 'XOR', ALU_NOT: 'NOT',
    ALU_SHL: 'SHL', ALU_SHR: 'SHR', ALU_ROL: 'ROL', ALU_ROR: 'ROR',
    ALU_ADD: 'ADD', ALU_SUB: 'SUB', 13: 'SUBR(予約)',
    ALU_CLC: 'CLC', ALU_SEC: 'SEC',
}


def generate_rom():
    rom = bytearray(8192)
    for cin in range(2):
        for code in range(16):
            for b in range(16):
                for a in range(16):
                    y, cout = alu(code, a, b, cin)
                    z = 1 if (y & 0xF) == 0 else 0
                    addr = a | (b << 4) | (code << 8) | (cin << 12)
                    rom[addr] = (y & 0xF) | ((cout & 1) << 4) | ((z & 1) << 5)
    return rom


def write_bin(rom, path):
    with open(path, 'wb') as f:
        f.write(rom)
    print(f'  BIN 出力: {os.path.basename(path)}  ({len(rom)} bytes)')


def write_intel_hex(rom, path):
    with open(path, 'w') as f:
        for i in range(0, len(rom), 16):
            chunk = rom[i:i + 16]
            n = len(chunk)
            addr = i & 0xFFFF
            chk = n + (addr >> 8) + (addr & 0xFF)
            line = ''.join(f'{b:02X}' for b in chunk)
            for b in chunk:
                chk += b
            chk = ((~chk) + 1) & 0xFF
            f.write(f':{n:02X}{addr:04X}00{line}{chk:02X}\n')
        f.write(':00000001FF\n')
    print(f'  HEX 出力: {os.path.basename(path)}  ({len(rom)} bytes)')


def spot_check(rom):
    def rd(code, a, b, cin):
        addr = a | (b << 4) | (code << 8) | (cin << 12)
        byte = rom[addr]
        return byte & 0xF, (byte >> 4) & 1, (byte >> 5) & 1  # y, Cout, Z

    # (code, a, b, cin, 期待y, 期待C, 期待Z, ラベル)
    cases = [
        (ALU_PASS_A, 0x5, 0x0, 0, 0x5, 0, 0, 'PASS_A a=5'),
        (ALU_PASS_B, 0x0, 0xA, 0, 0xA, 0, 0, 'PASS_B b=A'),
        (ALU_AND, 0xA, 0xC, 0, 0x8, 0, 0, 'AND A&C=8'),
        (ALU_OR,  0xA, 0x5, 0, 0xF, 0, 0, 'OR A|5=F'),
        (ALU_XOR, 0xF, 0xF, 0, 0x0, 0, 1, 'XOR F^F=0 Z=1'),
        (ALU_NOT, 0xA, 0x0, 0, 0x5, 0, 0, 'NOT ~A=5'),
        (ALU_SHL, 0x9, 0x0, 0, 0x2, 1, 0, 'SHL 9<<1=2 Cout=1(bit3)'),
        (ALU_SHR, 0x3, 0x0, 0, 0x1, 1, 0, 'SHR 3>>1=1 Cout=1(bit0)'),
        (ALU_ROL, 0x9, 0x0, 0, 0x3, 0, 0, 'ROL 1001→0011'),
        (ALU_ROR, 0x9, 0x0, 0, 0xC, 0, 0, 'ROR 1001→1100'),
        (ALU_ADD, 0x7, 0x9, 0, 0x0, 1, 1, 'ADD 7+9+0=0 C=1 Z=1'),
        (ALU_ADD, 0x7, 0x9, 1, 0x1, 1, 0, 'ADD 7+9+1=1 C=1 (Cin=1)'),
        (ALU_SUB, 0x5, 0x3, 1, 0x2, 1, 0, 'SUB 5-3-1+1=2 C=1 (Cin=1=SEC相当)'),
        (ALU_SUB, 0x3, 0x5, 1, 0xE, 0, 0, 'SUB 3-5=−2 borrow C=0'),
        (ALU_SUB, 0x5, 0x5, 1, 0x0, 1, 1, 'SUB 5-5=0 C=1 Z=1'),
        (ALU_SUB, 0x5, 0x2, 0, 0x2, 1, 0, 'SUB 5-2-1+0=2 (Cin=0=多倍長継続)'),
        (ALU_CLC, 0x7, 0x3, 1, 0x0, 0, 1, 'CLC Cout=0固定(y=0)'),
        (ALU_SEC, 0x7, 0x3, 0, 0x0, 1, 1, 'SEC Cout=1固定(y=0)'),
    ]
    print('\n=== スポットチェック ===')
    all_ok = True
    for code, a, b, cin, ey, ec, ez, label in cases:
        y, c, z = rd(code, a, b, cin)
        ok = (y == ey and c == ec and z == ez)
        all_ok &= ok
        print(f'  [{"OK" if ok else "NG"}] {label:38s} y={y:X} C={c} Z={z}')
    print('\n全ケース OK' if all_ok else '\nNG があります — cpu.alu/仕様を確認')
    return all_ok


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rom = generate_rom()
    print('--- 生成 ---')
    write_bin(rom, os.path.join(here, 'alu_rom.bin'))
    write_intel_hex(rom, os.path.join(here, 'alu_rom.hex'))
    ok = spot_check(rom)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
