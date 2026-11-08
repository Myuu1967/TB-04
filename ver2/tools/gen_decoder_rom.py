#!/usr/bin/env python3
"""TB-04 ver2 デコーダ ROM データ生成ツール

真理値表 `ver2/ver2_decoder_truthtable.csv`（＝正典）を読み、
デコーダ ROM-A/B/C（各1024バイト）の .bin/.hex を生成する。
ロジックはハードコードせず CSV を転記するだけ（仕様と乖離させない）。
真理値表を更新したら本スクリプトを再実行すれば ROM が作り直せる。

アドレス構成（10bit = 1024エントリ・ドラフト§10）:
  A0-A7 : byte1[7:0]（opcode プレフィックス＋オペランドニブル）
  A8    : C_prev
  A9    : Z_prev
  A10-A14: GND（未使用。1024エントリのみ有効）
  → addr = byte1 | (C_prev<<8) | (Z_prev<<9)

出力パッキング（20bit・3枚×8bit・ドラフト§10）:
  ROM-A: [D7]SEL_IMM [D6:5]SEL_B [D4]SEL_A [D3:0]AluCode
  ROM-B: [D7]SP_CD [D6]SP_CU [D5]PC_LOAD [D4]RegAddrSrc [D3]SEL_PC [D2:1]SEL_M [D0]SEL_Y
  ROM-C: [D7:5]予備(0) [D4]~SEL_Y [D3]WR [D2]Z_WE [D1]C_WE [D0]/WE
         ※ 2026-09-09 に割付を1つ繰り上げた。シート15のゲート整理で ~OE_RAM を WR 直結に
           したため /WR の受け先が消え、U705 の Q1-Q4 が C_WE/Z_WE/WR/~SEL_Y、Q5 が空きになった。
           ~SEL_Y = !SEL_Y（SEL_Y は ROM-B の D0）／WR = !(/WR)。/WR 自体は出力しない
           （真理値表の /WR 列は WR を導くための入力として残す）。受けは U705 の Q0-Q4。
         ※ C_WE/Z_WE は正論理（1=書く）。ハードは CLK_C = FCH1 & C_WE の AND 1個で受ける
           （正論理化=2026-07-17決定／ゲート相は EXE→FCH1 に 2026-08-13 変更）。
           /WE・/WR は負論理のまま。

PC_LOAD は真理値表で 0/1/C/!C/Z/!Z を取り、本ツールが各アドレスの C_prev/Z_prev で評価する。
"""

import csv
import os

CSV_NAME = 'ver2_decoder_truthtable.csv'

# NOP安全値（未マッチ byte1 用＝全書込禁止・非分岐）
NOP_SAFE = {
    'AluCode': 0, 'SEL_A': 0, 'SEL_B': 0, 'SEL_IMM': 0, 'SEL_Y': 0,
    'SEL_M': 0, 'SEL_PC': 0, 'RegAddrSrc': 0,
    '/WE': 1, '/WR': 1, 'C_WE': 0, 'Z_WE': 0,
    'SP_CU': 0, 'SP_CD': 0, 'PC_LOAD': '0',
}


def parse_pattern(pat):
    """'0000 xxxx' → (care_mask, want)。byte1 が (b & care)==want で一致。"""
    bits = pat.replace(' ', '')
    if len(bits) != 8:
        raise ValueError(f'byte1パターン長が不正: {pat!r}')
    care = 0
    want = 0
    for k, ch in enumerate(bits):
        bitpos = 7 - k
        if ch in '01':
            care |= (1 << bitpos)
            if ch == '1':
                want |= (1 << bitpos)
        elif ch in 'xX':
            pass
        else:
            raise ValueError(f'byte1パターンに不正文字: {ch!r} in {pat!r}')
    return care, want


def load_truthtable(path):
    """CSV を (care, want, controls) のリストへ。'-'行（複数枠予約表記）は無視。"""
    rules = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            pat = row['byte1'].strip()
            if '/' in pat or 'x' not in pat and len(pat.replace(' ', '')) != 8:
                # '0110/0111/1000' のような集約表記は truthtable では個別行なので通常来ない
                pass
            try:
                care, want = parse_pattern(pat)
            except ValueError:
                continue  # パターンとして解釈できない行はスキップ
            ctrl = {
                'AluCode': int(row['AluCode']),
                'SEL_A': int(row['SEL_A']),
                'SEL_B': int(row['SEL_B'], 2),
                'SEL_IMM': int(row['SEL_IMM']),
                'SEL_Y': int(row['SEL_Y']),
                'SEL_M': int(row['SEL_M'], 2),
                'SEL_PC': int(row['SEL_PC']),
                'RegAddrSrc': int(row['RegAddrSrc']),
                '/WE': int(row['/WE']),
                '/WR': int(row['/WR']),
                'C_WE': int(row['C_WE']),
                'Z_WE': int(row['Z_WE']),
                'SP_CU': int(row['SP_CU']),
                'SP_CD': int(row['SP_CD']),
                'PC_LOAD': row['PC_LOAD'].strip(),
            }
            rules.append((care, want, row['命令'].strip(), ctrl))
    return rules


def match(byte1, rules):
    for care, want, name, ctrl in rules:
        if (byte1 & care) == want:
            return name, ctrl
    return '(未定義)', NOP_SAFE


def eval_pc_load(token, c, z):
    return {
        '0': 0, '1': 1,
        'C': c, '!C': 1 - c,
        'Z': z, '!Z': 1 - z,
    }[token]


def pack(ctrl, c, z):
    pl = eval_pc_load(ctrl['PC_LOAD'], c, z)
    romA = ((ctrl['SEL_IMM'] & 1) << 7) | ((ctrl['SEL_B'] & 3) << 5) \
        | ((ctrl['SEL_A'] & 1) << 4) | (ctrl['AluCode'] & 0xF)
    romB = ((ctrl['SP_CD'] & 1) << 7) | ((ctrl['SP_CU'] & 1) << 6) \
        | ((pl & 1) << 5) | ((ctrl['RegAddrSrc'] & 1) << 4) \
        | ((ctrl['SEL_PC'] & 1) << 3) | ((ctrl['SEL_M'] & 3) << 1) \
        | (ctrl['SEL_Y'] & 1)
    romC = ((1 - (ctrl['SEL_Y'] & 1)) << 4) | ((1 - (ctrl['/WR'] & 1)) << 3) \
        | ((ctrl['Z_WE'] & 1) << 2) | ((ctrl['C_WE'] & 1) << 1) \
        | (ctrl['/WE'] & 1)
    return romA, romB, romC


def generate(rules):
    romA = bytearray(1024)
    romB = bytearray(1024)
    romC = bytearray(1024)
    for z in range(2):
        for c in range(2):
            for byte1 in range(256):
                _, ctrl = match(byte1, rules)
                addr = byte1 | (c << 8) | (z << 9)
                a, b, cc = pack(ctrl, c, z)
                romA[addr] = a
                romB[addr] = b
                romC[addr] = cc
    return romA, romB, romC


def write_bin(data, path):
    with open(path, 'wb') as f:
        f.write(data)
    print(f'  BIN 出力: {os.path.basename(path)}  ({len(data)} bytes)')


def write_intel_hex(data, path):
    with open(path, 'w') as f:
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            n = len(chunk)
            chk = n + (i >> 8) + (i & 0xFF)
            line = ''.join(f'{b:02X}' for b in chunk)
            for b in chunk:
                chk += b
            chk = ((~chk) + 1) & 0xFF
            f.write(f':{n:02X}{i:04X}00{line}{chk:02X}\n')
        f.write(':00000001FF\n')
    print(f'  HEX 出力: {os.path.basename(path)}  ({len(data)} bytes)')


def spot_check(rules, romA, romB, romC):
    """代表アドレスを読み戻して主要フィールドを確認（C/Z依存の分岐含む）。"""
    print('\n=== スポットチェック ===')
    def fields(byte1, c, z):
        addr = byte1 | (c << 8) | (z << 9)
        a, b, cc = romA[addr], romB[addr], romC[addr]
        return {
            'AluCode': a & 0xF, 'SEL_A': (a >> 4) & 1, 'SEL_B': (a >> 5) & 3,
            'SEL_IMM': (a >> 7) & 1,
            'SEL_Y': b & 1, 'SEL_M': (b >> 1) & 3, 'SEL_PC': (b >> 3) & 1,
            'RegAddrSrc': (b >> 4) & 1, 'PC_LOAD': (b >> 5) & 1,
            'SP_CU': (b >> 6) & 1, 'SP_CD': (b >> 7) & 1,
            '/WE': cc & 1, 'C_WE': (cc >> 1) & 1, 'Z_WE': (cc >> 2) & 1,
            'WR': (cc >> 3) & 1, '~SEL_Y': (cc >> 4) & 1,
        }
    # (byte1, C, Z, 期待{一部フィールド}, ラベル)
    cases = [
        (0x00, 0, 0, {'AluCode': 0, '/WE': 1, 'PC_LOAD': 0,
                      'C_WE': 0, 'Z_WE': 0,
                      'WR': 0, '~SEL_Y': 1}, 'NOP'),
        (0x30, 0, 0, {'AluCode': 2, 'SEL_B': 1, 'RegAddrSrc': 1, '/WE': 0}, 'LD'),
        (0xE0, 0, 0, {'PC_LOAD': 1}, 'JMP'),
        (0xE1, 1, 0, {'PC_LOAD': 1}, 'JC C=1→ロード'),
        (0xE1, 0, 0, {'PC_LOAD': 0}, 'JC C=0→非ロード'),
        (0xE2, 0, 0, {'PC_LOAD': 1}, 'JNC C=0→ロード'),
        (0xE3, 0, 1, {'PC_LOAD': 1}, 'JZ Z=1→ロード'),
        (0xE3, 0, 0, {'PC_LOAD': 0}, 'JZ Z=0→非ロード'),
        (0xE5, 0, 0, {'PC_LOAD': 1, 'SP_CD': 1, 'SEL_Y': 1,
                      'WR': 1, '~SEL_Y': 0}, 'CALL'),
        (0xE6, 0, 0, {'PC_LOAD': 1, 'SEL_PC': 1, 'SP_CU': 1}, 'RET'),
        (0xF0, 0, 0, {'AluCode': 12, 'C_WE': 1, 'Z_WE': 1, '/WE': 1}, 'CP'),
        (0xF9, 0, 0, {'AluCode': 11, 'C_WE': 1, 'Z_WE': 1, '/WE': 0}, 'ADD'),
        (0xFD, 0, 0, {'AluCode': 14, 'C_WE': 1, 'Z_WE': 0}, 'CLC'),
    ]
    all_ok = True
    for byte1, c, z, exp, label in cases:
        got = fields(byte1, c, z)
        ok = all(got[k] == v for k, v in exp.items())
        all_ok &= ok
        detail = ' '.join(f'{k}={got[k]}(!={v})' for k, v in exp.items() if got[k] != v)
        print(f'  [{"OK" if ok else "NG"}] byte1={byte1:#04x} C{c}Z{z} {label:22s} {detail}')
    print('\n全ケース OK' if all_ok else '\nNG があります — 真理値表/パッキングを確認')
    return all_ok


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(here, '..', CSV_NAME)
    if not os.path.exists(csv_path):
        print(f'エラー: 真理値表が見つかりません: {csv_path}')
        raise SystemExit(1)

    rules = load_truthtable(csv_path)
    print(f'真理値表: {CSV_NAME}  ({len(rules)} 規則)')
    romA, romB, romC = generate(rules)

    print('--- 生成 ---')
    for name, data in (('A', romA), ('B', romB), ('C', romC)):
        write_bin(data, os.path.join(here, f'decoder_rom{name}.bin'))
        write_intel_hex(data, os.path.join(here, f'decoder_rom{name}.hex'))

    ok = spot_check(rules, romA, romB, romC)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
