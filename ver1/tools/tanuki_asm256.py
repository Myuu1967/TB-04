#!/usr/bin/env python3
"""tanuki 4bit CPU アセンブラ（256語・マルチページ版）

tanuki_asm.py（16語・単一ページ版）の拡張。プログラムROMを 256語
（8bitアドレス空間）とみなし、16語ページを複数並べて格納する。
上位ニブル A4-A7 は手動セレクタで切り替える前提（PC本体は 4bit のまま）。

  - 下位ニブル A0-A3 = PC[3:0]（JMP/JZ/JNC で書き換わるのはここだけ）
  - 上位ニブル A4-A7 = ページ選択（手動セレクタ）

使い方:
    python tanuki_asm256.py program.asm
    python tanuki_asm256.py program.asm -o output_name
    python tanuki_asm256.py program.asm --no-bin

構文:
    ; コメント
    LABEL:          ラベル定義（英数字・アンダースコア）※ラベルは16語ページ単位スコープ
    NOP
    MOV   Ri, Rj
    MOVI  R0, Im    R0 は省略可: MOVI Im
    OUT   Ri
    OUTI  Im
    IN    Ri
    JMP   Addr/Label   ※同一16語ページ内のみ（下位4bitに符号化）
    JNC   Addr/Label
    JZ    Addr/Label
    AND   Ri, Rj
    OR    Ri, Rj
    XOR   Ri, Rj
    ADD   Ri, Rj
    ADDI  R0, Im    R0 は省略可: ADDI Im
    SUB   Ri, Rj
    SUBI  R0, Im    R0 は省略可: SUBI Im
    .org  N         配置アドレス設定（0x00〜0xFF）
    .byte N [, N]   生バイト埋め込み

レジスタ: R0〜R3
即値:     10進 (0〜15) または 16進 (0x0〜0xF)

【tanuki_asm.py との違い】
    - ROM を 256バイト出力（.org でページを並べる）
    - ラベルは16語ページ単位スコープ（デモ間で L0/L1 等の重複を許可）
    - JMP/JZ/JNC は飛び先の下位4bitのみを符号化。ページ跨ぎはエラー
"""

import sys
import os
import re
import argparse

ROM_SIZE = 256  # 8bitアドレス空間（上位ニブルは手動セレクタで選択）
PAGE_SIZE = 16  # 1ページ = 16語（PC[3:0]）


class AsmError(Exception):
    pass


# ── 値パーサ ─────────────────────────────────────────────────────

def parse_int(s: str) -> int:
    s = s.strip()
    if s.startswith(('0x', '0X')):
        return int(s, 16)
    if re.fullmatch(r'[0-9]+', s):
        return int(s, 10)
    raise ValueError(f"不正な値 '{s}' (10進 or 0x16進)")


def parse_reg(s: str) -> int:
    s = s.strip().upper()
    if re.fullmatch(r'R[0-3]', s):
        return int(s[1])
    raise AsmError(f"不正なレジスタ '{s}' (R0〜R3)")


def parse_imm(s: str, labels: dict, bits: int = 4) -> int:
    s = s.strip()
    key = s.upper()
    if key in labels:
        v = labels[key]
    else:
        try:
            v = parse_int(s)
        except ValueError:
            raise AsmError(f"未定義ラベルまたは不正な値 '{s}'")
    lim = 1 << bits
    if not (0 <= v < lim):
        raise AsmError(f"値 {v} が {bits}bit 範囲外 (0〜{lim - 1})")
    return v


# ── エンコーダ ───────────────────────────────────────────────────

OPCODES: dict[str, int] = {
    'NOP': 0, 'MOV': 1, 'MOVI': 2, 'OUT': 3,
    'OUTI': 4, 'IN': 5, 'JMP': 6, 'JNC': 7,
    'JZ': 8, 'AND': 9, 'OR': 10, 'XOR': 11,
    'ADD': 12, 'ADDI': 13, 'SUB': 14, 'SUBI': 15,
}


def _enc(opc: int, opr: int) -> int:
    return ((opr & 0xF) << 4) | (opc & 0xF)


def encode(mnem: str, ops: list, labels: dict, jresolve=None) -> int:
    m = mnem.upper()
    if m not in OPCODES:
        raise AsmError(f"不明な命令 '{mnem}'")

    n = len(ops)

    def R(k: int) -> int:
        return parse_reg(ops[k])

    def I(k: int, bits: int = 4) -> int:
        return parse_imm(ops[k], labels, bits)

    def need(cnt):
        if isinstance(cnt, int):
            if n != cnt:
                raise AsmError(f"{m}: オペランド {cnt} 個必要 ({n} 個)")
        else:
            if n not in cnt:
                raise AsmError(f"{m}: オペランド {tuple(cnt)} 個のいずれか ({n} 個)")

    if m == 'NOP':
        return _enc(0, 0)

    if m == 'MOV':
        need(2)
        return _enc(1, (R(0) << 2) | R(1))

    if m == 'MOVI':
        need((1, 2))
        im = I(1) if n == 2 else I(0)
        return _enc(2, im)

    if m == 'OUT':
        need(1)
        return _enc(3, R(0) << 2)

    if m == 'OUTI':
        need(1)
        return _enc(4, I(0))

    if m == 'IN':
        need(1)
        return _enc(5, R(0) << 2)

    if m in ('JMP', 'JNC', 'JZ'):
        need(1)
        if jresolve is not None:
            return _enc(OPCODES[m], jresolve(ops[0]))
        return _enc(OPCODES[m], I(0))

    if m in ('AND', 'OR', 'XOR', 'ADD', 'SUB'):
        need(2)
        return _enc(OPCODES[m], (R(0) << 2) | R(1))

    if m in ('ADDI', 'SUBI'):
        need((1, 2))
        im = I(1) if n == 2 else I(0)
        return _enc(OPCODES[m], im)

    raise AsmError(f"内部エラー '{m}'")


# ── 逆アセンブラ ────────────────────────────────────────────────

def disasm(b: int) -> str:
    opc = b & 0xF
    opr = (b >> 4) & 0xF
    ri = (opr >> 2) & 3
    rj = opr & 3
    if opc == 0:  return "NOP"
    if opc == 1:  return f"MOV   R{ri}, R{rj}"
    if opc == 2:  return f"MOVI  R0, {opr}"
    if opc == 3:  return f"OUT   R{ri}"
    if opc == 4:  return f"OUTI  {opr}"
    if opc == 5:  return f"IN    R{ri}"
    if opc == 6:  return f"JMP   .{opr:X}"
    if opc == 7:  return f"JNC   .{opr:X}"
    if opc == 8:  return f"JZ    .{opr:X}"
    if opc == 9:  return f"AND   R{ri}, R{rj}"
    if opc == 10: return f"OR    R{ri}, R{rj}"
    if opc == 11: return f"XOR   R{ri}, R{rj}"
    if opc == 12: return f"ADD   R{ri}, R{rj}"
    if opc == 13: return f"ADDI  R0, {opr}"
    if opc == 14: return f"SUB   R{ri}, R{rj}"
    if opc == 15: return f"SUBI  R0, {opr}"
    return "???"


# ── パーサ ──────────────────────────────────────────────────────

_LABEL_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*')


def tokenize(raw: str):
    """Returns (label|None, mnem|None, ops_list, raw)"""
    line = raw
    if ';' in line:
        line = line[:line.index(';')]
    line = line.strip()

    label = None
    m = _LABEL_RE.match(line)
    if m:
        label = m.group(1).upper()
        line = line[m.end():].strip()

    if not line:
        return label, None, [], raw

    parts = line.split(None, 1)
    mnem = parts[0]
    ops_str = parts[1] if len(parts) > 1 else ''
    ops = [o.strip() for o in ops_str.split(',') if o.strip()]
    return label, mnem, ops, raw


# ── 2パスアセンブル ─────────────────────────────────────────────

def assemble(source: str):
    lines = source.splitlines()
    tokens = []
    for ln, raw in enumerate(lines, 1):
        label, mnem, ops, raw_ = tokenize(raw)
        tokens.append((ln, label, mnem, ops, raw))

    # 第1パス: ページ単位ラベル収集（page = addr // 16）
    pages: dict[int, dict[str, int]] = {}
    addr = 0
    for ln, label, mnem, ops, raw in tokens:
        if label:
            pg = addr // PAGE_SIZE
            d = pages.setdefault(pg, {})
            if label in d:
                sys.exit(f"エラー {ln}行: ラベル重複 '{label}' "
                         f"(ページ 0x{pg:X}0)")
            d[label] = addr

        if mnem is None:
            continue
        mu = mnem.upper()

        if mu == '.ORG':
            try:
                addr = parse_int(ops[0]) if ops else 0
            except (ValueError, IndexError):
                sys.exit(f"エラー {ln}行: .org の引数が不正")
            if not (0 <= addr < ROM_SIZE):
                sys.exit(f"エラー {ln}行: .org 0x{addr:X} が範囲外 (0x00-0xFF)")
        elif mu == '.BYTE':
            addr += len(ops)
        else:
            if addr >= ROM_SIZE:
                sys.exit(f"エラー {ln}行: アドレス 0x{addr:X} がROM範囲外 (0x00-0xFF)")
            addr += 1

    # ジャンプ先解決: 同一16語ページ内のみ・下位4bitに符号化
    def resolve_jump(operand: str, page: int, ln: int) -> int:
        key = operand.strip().upper()
        here = pages.get(page, {})
        if key in here:
            return here[key] & 0xF
        # 別ページに同名ラベルがある場合は明示エラー
        for pg, dd in pages.items():
            if key in dd:
                sys.exit(f"エラー {ln}行: ジャンプ先 '{operand}' は別ページ "
                         f"(0x{pg:X}0)。JMP/JZ/JNC は同一16語ページ内のみ")
        # 数値指定
        try:
            v = parse_int(operand)
        except ValueError:
            sys.exit(f"エラー {ln}行: 未定義ラベルまたは不正な飛び先 '{operand}'")
        if v < PAGE_SIZE:
            return v  # 下位4bit直接指定（現ページ内）
        if v // PAGE_SIZE != page:
            sys.exit(f"エラー {ln}行: 飛び先 0x{v:X} は別ページ。"
                     f"JMP/JZ/JNC は同一16語ページ内のみ")
        return v & 0xF

    # 第2パス: エンコード
    rom = bytearray(ROM_SIZE)
    listing = []
    addr = 0

    for ln, label, mnem, ops, raw in tokens:
        if mnem is None:
            listing.append({'addr': None, 'bytes': None, 'raw': raw})
            continue

        mu = mnem.upper()

        if mu == '.ORG':
            addr = parse_int(ops[0]) if ops else 0
            listing.append({'addr': None, 'bytes': None, 'raw': raw})
            continue

        if mu == '.BYTE':
            byte_list = []
            start = addr
            for op in ops:
                try:
                    v = parse_int(op) & 0xFF
                except ValueError:
                    sys.exit(f"エラー {ln}行: .byte 値が不正 '{op}'")
                if addr < ROM_SIZE:
                    rom[addr] = v
                byte_list.append(v)
                addr += 1
            listing.append({'addr': start, 'bytes': byte_list, 'raw': raw})
            continue

        page = addr // PAGE_SIZE
        jr = lambda operand, _p=page, _ln=ln: resolve_jump(operand, _p, _ln)
        try:
            b = encode(mnem, ops, pages.get(page, {}), jr)
        except AsmError as e:
            sys.exit(f"エラー {ln}行: {e}")

        if addr < ROM_SIZE:
            rom[addr] = b
        listing.append({'addr': addr, 'bytes': [b], 'raw': raw})
        addr += 1

    # リスティング表示用にラベルを平坦化（重複名はアドレスで一意化）
    name_count: dict[str, int] = {}
    for dd in pages.values():
        for name in dd:
            name_count[name] = name_count.get(name, 0) + 1
    flat: dict[str, int] = {}
    for pg in sorted(pages):
        for name, a in pages[pg].items():
            key = name if name_count[name] == 1 else f"{name}@{pg:X}0"
            flat[key] = a

    return rom, flat, listing


# ── リスティング出力 ─────────────────────────────────────────────

def print_listing(listing: list, labels: dict):
    rev = {v: k for k, v in labels.items()}
    shown = set()

    print("Addr | Hex  | Disasm                   | Source")
    print("-----|------|--------------------------|" + "-" * 35)

    for entry in listing:
        addr = entry['addr']
        blist = entry['bytes']
        raw = entry['raw'].rstrip()

        if addr is not None:
            lbl = rev.get(addr)
            if lbl and lbl not in shown:
                shown.add(lbl)

        if addr is None:
            print(f"     |      |                          | {raw}")
        elif blist is None or len(blist) == 0:
            print(f" {addr:02X}  |      |                          | {raw}")
        elif len(blist) == 1:
            b = blist[0]
            print(f" {addr:02X}  | {b:02X}   | {disasm(b):<24} | {raw}")
        else:
            hexstr = ' '.join(f'{b:02X}' for b in blist)
            print(f" {addr:02X}  | {hexstr:<4} |                          | {raw}")


# ── ファイル出力 ─────────────────────────────────────────────────

def write_bin(data: bytearray, path: str):
    with open(path, 'wb') as f:
        f.write(data)
    print(f"BIN: {path}  ({len(data)} bytes)")


def write_hex(data: bytearray, path: str, base: int = 0):
    with open(path, 'w') as f:
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            n = len(chunk)
            a = base + i
            chk = n + (a >> 8) + (a & 0xFF)
            d = ''
            for b in chunk:
                d += f'{b:02X}'
                chk += b
            chk = ((~chk) + 1) & 0xFF
            f.write(f':{n:02X}{a:04X}00{d}{chk:02X}\n')
        f.write(':00000001FF\n')
    print(f"HEX: {path}")


# ── main ─────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='tanuki 4bit CPU アセンブラ（256語・マルチページ版）')
    ap.add_argument('source', help='ソースファイル (.asm)')
    ap.add_argument('-o', '--output', help='出力ファイル名（拡張子なし）')
    ap.add_argument('--no-bin', action='store_true', help='BIN/HEX を出力しない')
    args = ap.parse_args()

    # Windowsコンソール(cp932)でソース中のem-dash等を表示できるようにする
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

    try:
        with open(args.source, encoding='utf-8') as f:
            src = f.read()
    except FileNotFoundError:
        sys.exit(f"ファイルが見つかりません: {args.source}")

    rom, labels, listing = assemble(src)

    print_listing(listing, labels)
    print()

    if labels:
        print("ラベル一覧:")
        for k, v in sorted(labels.items(), key=lambda x: x[1]):
            print(f"  {k:16s}: 0x{v:02X}  (page 0x{v // PAGE_SIZE:X}0)")
        print()

    if not args.no_bin:
        base = args.output or os.path.splitext(args.source)[0]
        write_bin(rom, base + '.bin')
        write_hex(rom, base + '.hex')


if __name__ == '__main__':
    main()
