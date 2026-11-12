#!/usr/bin/env python3
"""TB-04 ver2 ブリングアップ用テストROM生成ツール（命令ROM U604・16バンク）

1バンク=256バイト。SW601 の位置 n = バンク n（A8-A11）。
各バンクのプログラムは ROM 領域 0x00-0xBF に収める（0xC0 以降は RAM が読まれる）。
依存順（2026-10-25 決定）: 確かめる命令は1バンク1グループ、ほかは確認済みの命令だけを使う。

出力:
  test_rom.bin / test_rom.hex   … 4096バイト（16バンク）。T48 で 28C256 の先頭へ書く
  --json PATH                   … 期待値トレース（Word 資料の材料）
  --demo                        … 展示用デモROM demo_rom.bin / .hex（DEMO_BANKS）

期待値は sim/cpu.py で求める。実機はリセットでレジスタ（161の~MR）を0にするが、
C/Z（74の CLR/PR は VDD 固定）・OUT（377）・RAM は初期化しないので、
それらを2通り（全0／全1）にして走らせ、結果が食い違う値は「?」（＝不定）として出す。
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sim'))
from asm import Asm, disasm  # noqa: E402
from cpu import TB04CPU      # noqa: E402
from gen_alu_rom import write_intel_hex  # noqa: E402

BANK_SIZE = 256
ROM_LIMIT = 0xC0
N_BANKS = 16


def pad_to(p, addr):
    """NOP で番地 addr まで埋める（addr は偶数）。"""
    while len(p.prog) * 2 < addr:
        p.NOP()


# ---------------------------------------------------------------------
# 各バンクのプログラム
# ---------------------------------------------------------------------
def bank_nop():
    """NOP 95個（byte1 下位とbyte2を毎回変える）→ 0xBE で JMP 0x00。"""
    p = Asm()
    for i in range(95):
        p._add('NOPX', i)
    p.JMP(0x00)
    return p


def bank_jmp():
    p = Asm()
    p.JMP(0xAA)          # 0x00 → 0xAA（10101010）
    p.MOVI(0, 0xF)       # 0x02 飛ばされる
    pad_to(p, 0x54)
    p.label('s3')
    p.HALT()             # 0x54（01010100）で停止
    pad_to(p, 0xAA)
    p.JMP('s3')          # 0xAA → 0x54
    p.MOVI(0, 0xF)       # 飛ばされる
    return p


def movi_mark(p, r, v):
    """MOVI Ri,v。byte2 の下位ニブル（MOVI では未使用）を Ri+1 にして表示で見分ける。"""
    p._add('DATA', 0x20 | (v & 0xF), ((r & 7) << 4) | ((r + 1) & 0xF))


def bank_movi():
    p = Asm()
    for r, v in enumerate((1, 2, 4, 8, 5, 0xA, 0xF, 0)):
        movi_mark(p, r, v)
    p.label('B')
    for r, v in enumerate((0xE, 0xD, 0xB, 7, 0xA, 5, 0, 0xF)):
        movi_mark(p, r, v)
    p.HALT()
    return p


def preset(p, vals=(1, 2, 4, 8, 5, 0xA, 0xF, 0)):
    for r, v in enumerate(vals):
        p.MOVI(r, v)


def bank_mov():
    p = Asm()
    preset(p)
    for d in range(7, 0, -1):     # R7←R6 … R1←R0（全レジスタが送り元・送り先になる）
        p.MOV(d, d - 1)
    p.MOV(0, 7)
    p.HALT()
    return p


def bank_out():
    p = Asm()
    for port, v in enumerate((1, 2, 4, 8)):
        p.OUTI(port, v)
    for port, v in enumerate((0xE, 0xD, 0xB, 7)):
        p.OUTI(port, v)
    preset(p)
    for r in range(8):            # 送り元 R0-R7 を1つずつ OUT0 へ
        p.OUT(0, r)
    for port, r in enumerate((4, 5, 6, 7)):
        p.OUT(port, r)
    p.HALT()
    return p


def bank_addi():
    p = Asm()
    p.SEC(); p.CLC(); p.SEC()     # C の LED が 1→0→1
    p.MOVI(1, 0)                  # MOVI は C を変えない（C=1 のまま）
    p.MOVI(0, 0)
    p.CLC(); p.ADDI(0, 1)         # 1  C0 Z0
    p.CLC(); p.ADDI(0, 0xF)       # 0  C1 Z1
    p.ADDI(0, 0)                  # 0+0+Cin(1)=1  C0 Z0
    p.SEC(); p.SUBI(0, 1)         # 0  C1(借りなし) Z1
    p.SEC(); p.SUBI(0, 1)         # F  C0(借り)    Z0
    p.CLC(); p.SUBI(0, 0)         # F-0-1=E  C1 Z0
    p.MOVI(7, 7)
    p.CLC(); p.ADDI(7, 8)         # F  C0 Z0
    p.HALT()
    return p


def bank_add():
    p = Asm()
    p.MOVI(0, 7); p.MOVI(1, 9)
    p.CLC(); p.ADD(0, 1)          # 0  C1 Z1
    p.MOVI(2, 3); p.MOVI(3, 5)
    p.SEC(); p.SUB(2, 3)          # E  C0 Z0
    p.SEC(); p.CP(3, 3)           # R3 不変  C1 Z1
    p.SEC(); p.CP(2, 3)           # E-5  C1 Z0
    p.SEC(); p.CP(3, 2)           # 5-E  C0 Z0
    p.MOVI(6, 6); p.MOVI(7, 0xC)
    p.CLC(); p.ADD(6, 7)          # 2  C1 Z0
    p.HALT()
    return p


def bank_logic():
    p = Asm()
    p.MOVI(0, 0xC); p.MOVI(1, 0xA)
    p.SEC()                       # 論理演算は C を変えない（最後まで C=1）
    p.MOV(2, 0); p.AND(2, 1)      # 8
    p.MOV(3, 0); p.OR(3, 1)       # E
    p.MOV(4, 0); p.XOR(4, 1)      # 6
    p.MOV(5, 0); p.NOT(5)         # 3
    p.MOVI(6, 5); p.AND(6, 1)     # 0  Z1
    p.MOV(7, 1); p.XOR(7, 7)      # 0  Z1
    p.HALT()
    return p


def bank_shift():
    p = Asm()
    p.MOVI(0, 9); p.SHL(0); p.SHL(0)    # 2 C1 → 4 C0
    p.MOVI(1, 9); p.SHR(1); p.SHR(1)    # 4 C1 → 2 C0
    p.MOVI(4, 8); p.SHL(4)              # 0 C1 Z1
    p.MOVI(2, 9); p.ROL(2); p.ROL(2)    # 3 → 6（フラグ不変）
    p.MOVI(3, 9); p.ROR(3); p.ROR(3)    # C → 6（フラグ不変）
    p.HALT()
    return p


def bank_jcc():
    """8ケース。正しい経路なら OUT0 にケース番号を出して進む。誤れば OUT3=F で停止。
    C/Z の組は C を CLC/SEC、Z を XOR(=1)/OR(=0) で作る（互いに干渉しない）。"""
    p = Asm()
    p.OUTI(3, 0); p.OUTI(0, 0)
    p.MOVI(0, 0); p.MOVI(1, 1)

    def flags(c, z):
        (p.SEC if c else p.CLC)()
        if z:
            p.XOR(2, 2)          # Z=1（C 不変）
        else:
            p.MOV(2, 1); p.OR(2, 2)   # Z=0（C 不変）

    cases = [  # (命令, C, Z, 分岐するか)
        ('JC', 1, 0, True), ('JC', 0, 1, False),
        ('JNC', 0, 1, True), ('JNC', 1, 0, False),
        ('JZ', 0, 1, True), ('JZ', 1, 0, False),
        ('JNZ', 1, 0, True), ('JNZ', 0, 1, False),
    ]
    for k, (op, c, z, taken) in enumerate(cases, 1):
        flags(c, z)
        if taken:
            getattr(p, op)(f'ok{k}')
            p.JMP('fail')
            p.label(f'ok{k}')
        else:
            getattr(p, op)('fail')
        p.OUTI(0, k)
    p.OUTI(3, 0xA)               # 全ケース通過
    p.HALT()
    p.label('fail')
    p.OUTI(3, 0xF)
    p.HALT()
    return p


def bank_mem():
    p = Asm()
    p.STI(0xC0, 5); p.STI(0xEF, 0xA)
    p.LD(0, 0xC0); p.LD(1, 0xEF)          # 5, A
    p.MOVI(2, 0xC); p.ST(0xD5, 2)
    p.MOVI(3, 3); p.ST(0xEA, 3)
    p.LD(4, 0xD5); p.LD(5, 0xEA)          # C, 3
    p.STI(0xC0, 0xA); p.LD(6, 0xC0)       # 同じ番地を書き換え → A
    p.LD(7, 'tbl')                        # ROM 領域の定数（下位ニブル）
    p.HALT()
    p.label('tbl')
    p._add('DATA', 0x09, 0x00)            # 0x09 = NOP として置いた定数9
    return p


def bank_stack():
    p = Asm()
    preset(p, (1, 2, 4, 8, 0, 0, 0, 0))
    for r in range(4):
        p.PUSH(r)                         # SP 7→6→5→4→3
    for r in range(4, 8):
        p.POP(r)                          # R4=8 R5=4 R6=2 R7=1、SP→7
    p.HALT()
    return p


def bank_call():
    p = Asm()
    p.MOVI(0, 0); p.OUTI(0, 0)
    p.CALL('sub1'); p.OUTI(0, 1)
    p.CALL('sub2'); p.OUTI(0, 2)
    p.HALT()
    pad_to(p, 0x96)
    p.label('sub2')                       # 0x96（ネスト：sub1 を2回）
    p.CALL('sub1'); p.CALL('sub1'); p.RET()
    pad_to(p, 0xB6)
    p.label('sub1')                       # 0xB6
    p.CLC(); p.ADDI(0, 1); p.RET()
    return p


def bank_in():
    p = Asm()
    p.label('loop')
    for port in range(4):
        p.IN(port, port); p.OUT(port, port)   # IN[k] → Rk → OUT[k]
    p.JMP('loop')
    return p


def bank_demo():
    from programs import counter
    p, _ = counter()
    return p


def bank_showcase():
    from programs import showcase
    p, _ = showcase()
    return p


BANKS = [
    ('NOP', bank_nop, 'なし', 'PC_Q・OPC/OPR・MD の表示'),
    ('JMP', bank_jmp, 'なし', 'PC_Q が 00→AA→54 で止まる'),
    ('MOVI', bank_movi, 'JMP', 'レジスタ LED 32個'),
    ('MOV', bank_mov, 'MOVI・JMP', 'レジスタ LED'),
    ('OUTI・OUT', bank_out, 'MOVI・JMP', 'OUT の LED・7セグ'),
    ('CLC・SEC・ADDI・SUBI', bank_addi, 'MOVI・JMP', 'C/Z の LED・レジスタ LED'),
    ('ADD・SUB・CP', bank_add, 'バンク5', 'C/Z・レジスタ'),
    ('AND・OR・XOR・NOT', bank_logic, 'バンク5', 'C/Z・レジスタ'),
    ('SHL・SHR・ROL・ROR', bank_shift, 'バンク5', 'C/Z・レジスタ'),
    ('JC・JNC・JZ・JNZ', bank_jcc, 'バンク4〜7', 'OUT0=ケース番号・OUT3（A=合格／F=不合格）'),
    ('STI・ST・LD', bank_mem, 'バンク9まで', 'MD 表示・レジスタ'),
    ('PUSH・POP', bank_stack, 'バンク10', 'SP の LED・レジスタ'),
    ('CALL・RET', bank_call, 'バンク11', 'PC_Q・SP・R0・OUT0'),
    ('IN', bank_in, 'バンク9まで', 'DIP → OUT のエコー・Z の LED'),
    ('総合（カウンタ）', bank_demo, 'すべて', 'IN0=0 でダウン／非0 でアップ'),
    ('展示（単語→4桁カウンタ）', bank_showcase, 'すべて', '命令表示4桁の単語（4Hz）・OUT 2×2'),
]


# ---------------------------------------------------------------------
# 展示用デモROM（--demo）。割当は ver2/DEVLOG 2026-11-08(3)。
# 9 以降は新作ができるまで既存デモで埋める（後で差し替える）。
# ---------------------------------------------------------------------
def clear_out(p, ports=(1, 2, 3)):
    """先頭に OUTI port,0 を足す（OUT はリセットで不定＝使わないポートの7セグを消す）。"""
    q = Asm()
    for port in ports:
        q.OUTI(port, 0)
    off = len(q.prog) * 2
    q.labels = {k: v + off for k, v in p.labels.items()}
    q.prog += p.prog
    return q


def demo(name, clear=True):
    def fn():
        import programs
        p, _ = programs.PROGRAMS[name]()
        return clear_out(p) if clear else p
    return fn


DEMO_BANKS = [
    ('showcase', demo('showcase', clear=False), '4Hz で単語→1kHz でカウンタ'),
    ('counter', demo('counter'), 'IN0=0 でダウン／非0 でアップ'),
    ('led_flow', demo('led_flow'), 'IN0=0 で8コマ／非0 で4コマ'),
    ('fibonacci', demo('fibonacci'), 'mod16・周期24'),
    ('life_ca', demo('life_ca'), '周期15・IN0 の下位3bitでセル注入'),
    ('pred_prey', demo('pred_prey'), 'OUT0 に草食・肉食を交互に'),
    ('kakezan', demo('kakezan'), '4×4 の16積を出して停止'),
    ('hanoi', demo('hanoi', clear=False), '4枚・CALL/RET再帰・512Hz'),
    ('ishitori', demo('ishitori', clear=False), 'IN3: 1個/2個/3個/新ゲーム・1024Hz'),
    ('kaprekar', demo('kaprekar', clear=False), 'DIPで初期値→6174・1024Hz'),
    ('rule_ca', demo('rule_ca', clear=False), 'Rule90/30・IN3 bit0=90 他=30・1024Hz'),
    ('collatz', demo('collatz', clear=False), 'DIPで初期値(0なら27)・1024Hz'),
    ('calc_normal', demo('calc_normal', clear=False), 'キーパッド(IN0/IN1)・四則・1キー1桁'),
    ('calc_rpn', demo('calc_rpn', clear=False), 'キーパッド・逆ポーランド・＋−×'),
    ('ecosystem', demo('ecosystem', clear=False), 'IN3: 草を植える/狩る・2048Hz'),
    ('melody', demo('melody', clear=False), 'OUT0→Pico で音と光・1024Hz'),
]
# 外したもの（programs.py には残る）: ramen_timer・sec_count（何分も見ないと分からない時間もの。
# ラーメンタイマーは ver1 実機で見せられる）・calc（calc_normal/calc_rpn に置き換え）


# ---------------------------------------------------------------------
def assemble(p):
    """Asm に NOPX/DATA の擬似命令を足して組み立てる。"""
    out = []
    for idx, (op, args) in enumerate(p.prog):
        if op == 'NOPX':
            i = args[0]
            out += [i & 0xF, i & 0xFF]
        elif op == 'DATA':
            out += [args[0] & 0xFF, args[1] & 0xFF]
        else:
            p_one = Asm()
            p_one.labels = p.labels
            p_one.prog = [(op, args)]
            b = p_one._resolve
            from asm import encode
            out += list(encode(op, args, addr=idx * 2, resolve=b))
    return out


def run_trace(rom, in_ports, max_instr, init):
    c = TB04CPU(rom)
    v = 0xF if init else 0
    c.R = [0] * 8                 # レジスタはリセットで0（2026-10-26 実機で確認）
    c.C = c.Z = 1 if init else 0
    c.out_ports = [v] * 4
    for a in range(0xC0, 0x100):
        c.mem[a] = v
    c.in_ports = list(in_ports)
    rows = []
    for _ in range(max_instr):
        pc = c.PC
        b1, b2 = c.mem[pc], c.mem[(pc + 1) & 0xFF]
        c.step()
        rows.append({'addr': pc, 'b1': b1, 'b2': b2, 'asm': disasm(b1, b2),
                     'PC': c.PC, 'R': list(c.R), 'C': c.C, 'Z': c.Z, 'SP': c.SP,
                     'OUT': list(c.out_ports)})
        if c.halted:
            break
    return rows


def merge(r0, r1):
    """初期状態2通りのトレースを突き合わせ、違う値は '?' にする。"""
    rows = []
    for a, b in zip(r0, r1):
        assert a['addr'] == b['addr'] and a['PC'] == b['PC'], '経路が初期状態に依存している'
        f = lambda x, y: x if x == y else '?'
        rows.append({**a, 'R': [f(x, y) for x, y in zip(a['R'], b['R'])],
                     'C': f(a['C'], b['C']), 'Z': f(a['Z'], b['Z']),
                     'OUT': [f(x, y) for x, y in zip(a['OUT'], b['OUT'])]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json')
    ap.add_argument('--demo', action='store_true', help='展示用デモROM（demo_rom.bin/hex）を出す')
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))

    if args.demo:
        image = bytearray(BANK_SIZE * N_BANKS)
        for n, (name, fn, look) in enumerate(DEMO_BANKS):
            rom = assemble(fn())
            assert len(rom) <= ROM_LIMIT, f'バンク{n} が 0xC0 を超えた（{len(rom):#x}）'
            image[n * BANK_SIZE:n * BANK_SIZE + len(rom)] = bytes(rom)
            print(f'バンク{n:2d} {name:<12} {len(rom):3d}バイト  {look}')
        with open(os.path.join(here, 'demo_rom.bin'), 'wb') as f:
            f.write(image)
        write_intel_hex(image, os.path.join(here, 'demo_rom.hex'))
        return

    image = bytearray(BANK_SIZE * N_BANKS)
    report = []
    for n, (name, fn, dep, look) in enumerate(BANKS):
        p = fn()
        rom = assemble(p)
        assert len(rom) <= ROM_LIMIT, f'バンク{n} が 0xC0 を超えた（{len(rom):#x}）'
        image[n * BANK_SIZE:n * BANK_SIZE + len(rom)] = bytes(rom)
        in_ports = (5, 0xA, 3, 0xC) if name == 'IN' else (1, 0, 0, 0)
        limit = {'NOP': 96, '予備': 96, 'IN': 9}.get(name, 40 if n == 14 else 200)
        rows = merge(run_trace(rom, in_ports, limit, False),
                     run_trace(rom, in_ports, limit, True))
        report.append({'bank': n, 'name': name, 'dep': dep, 'look': look,
                       'size': len(rom), 'in_ports': in_ports, 'rows': rows})
        print(f'バンク{n:2d} {name:<18} {len(rom):3d}バイト  {len(rows):3d}命令')

    with open(os.path.join(here, 'test_rom.bin'), 'wb') as f:
        f.write(image)
    write_intel_hex(image, os.path.join(here, 'test_rom.hex'))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False)


if __name__ == '__main__':
    main()
