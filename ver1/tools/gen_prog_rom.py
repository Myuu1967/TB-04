#!/usr/bin/env python3
"""
プログラム ROM データ生成ツール（TB-04 4bitCPU）

命令バイトフォーマット:
  D[3:0] = OPC[3:0]  (下位ニブル)
  D[7:4] = OPR[3:0]  (上位ニブル)

U14 (28C256) アドレス:
  A0-A3: PC[3:0]（実使用）
  A4-A7: GND または PC上位（PCBに依存）
  A8-A14: GND

出力ファイル:
  prog_rom.bin  256バイト（A0-A7の全範囲をカバー）
  prog_rom.hex  Intel HEX形式
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sim'))
from asm import disasm

ROM_SIZE = 256  # A0-A7 = 8bit分をカバー（32768バイト中の有効範囲）


# ---------- プログラム定義 ----------

def prog_test_nop():
    """
    ROMデータ読み込み確認用テストプログラム（32バイト NOP）

    アドレス 0x00-0x0F: NOP, OPR = アドレス値  (バイト値: 0x00, 0x10, ..., 0xF0)
    アドレス 0x10-0x1F: NOP, OPR = アドレス-16 (バイト値: 0x00, 0x10, ..., 0xF0)
    アドレス 0x20-0xFF: NOP, OPR = 0 (バイト値: 0x00)

    LEDモニタで OPR（上位ニブル）をアドレスごとに確認できる。
    すべて NOP なので CPU に悪影響なし。
    """
    rom = bytearray(ROM_SIZE)
    for addr in range(32):
        opc = 0            # NOP = 0x0
        opr = addr % 16
        rom[addr] = (opr << 4) | opc
    # 0x20 以降は 0x00 (NOP, OPR=0) のまま
    return rom


# ---------- 出力関数 ----------

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


def dump(rom, n=32):
    """先頭 n バイトを逆アセンブル表示"""
    print(f"\n=== ROM ダンプ（先頭 {n} バイト） ===")
    print("Addr | Hex  | OPC | OPR | Disassembly")
    print("-----|------|-----|-----|--------------------")
    for addr in range(n):
        b = rom[addr]
        opc = b & 0xF
        opr = (b >> 4) & 0xF
        print(f" {addr:3d} | 0x{b:02X} |  {opc:X}  |  {opr:X}  | {disasm(b)}")


# ---------- メイン ----------

if __name__ == '__main__':
    out_dir = os.path.dirname(os.path.abspath(__file__))

    rom = prog_test_nop()

    write_bin(rom, os.path.join(out_dir, 'prog_rom.bin'))
    write_intel_hex(rom, os.path.join(out_dir, 'prog_rom.hex'))

    dump(rom, n=32)
