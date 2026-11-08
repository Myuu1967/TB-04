"""TB-04 ver2 命令単位シミュレータ 論理検証テスト

設計の要所を突く自己テスト（論点4の機能検証）:
  ADD/SUB の ADC/SBC（Cin=C_prev）と CLC/SEC 初期化、CP 比較、
  LD/ST RAM往復、CALL/RET、PUSH/POP（post-dec/pre-inc・LIFO）、
  IN/OUT メモリマップド、多倍長ゼロ判定（Zin連鎖）。

実行:  python test_cpu.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpu import TB04CPU
from cpu_phase import TB04CPUPhase
from asm import Asm

_pass = 0
_fail = 0


def check(name, cond, detail=''):
    global _pass, _fail
    if cond:
        _pass += 1
        print(f'  [OK]   {name}')
    else:
        _fail += 1
        print(f'  [FAIL] {name}  {detail}')


def run(asm, max_instr=200, **kw):
    cpu = TB04CPU(asm.assemble(), **kw)
    cpu.run(max_instr=max_instr)
    return cpu


# --- A: ADD とキャリー/ゼロ（CLC 初期化）---
def test_add_carry():
    p = Asm()
    p.CLC(); p.MOVI(0, 7); p.MOVI(1, 9); p.ADD(0, 1); p.HALT()
    c = run(p)
    check('ADD 7+9 → R0=0', c.R[0] == 0, f'R0={c.R[0]}')
    check('ADD 7+9 → C=1（桁上げ）', c.C == 1, f'C={c.C}')
    check('ADD 7+9 → Z=1（結果0）', c.Z == 1, f'Z={c.Z}')


# --- B: CP（SEC で Cin=1 → 真の減算による比較）---
def test_compare():
    for a, b, exp_c in [(5, 3, 1), (3, 5, 0), (4, 4, 1)]:
        p = Asm()
        p.SEC(); p.MOVI(0, a); p.MOVI(1, b); p.CP(0, 1); p.HALT()
        c = run(p)
        # C=1 ⇔ ボローなし ⇔ a>=b
        check(f'CP {a} vs {b}: C={exp_c}(a>=b?)', c.C == exp_c, f'C={c.C}')
        check(f'CP {a} vs {b}: R0非破壊', c.R[0] == a, f'R0={c.R[0]}')
    # 等値は Z=1
    p = Asm(); p.SEC(); p.MOVI(0, 4); p.MOVI(1, 4); p.CP(0, 1); p.HALT()
    c = run(p)
    check('CP 4 vs 4: Z=1', c.Z == 1, f'Z={c.Z}')


# --- C: LD/ST RAM 往復 ---
def test_load_store():
    p = Asm()
    p.STI(0xC0, 9)          # MEM[0xC0]=9
    p.MOVI(0, 3); p.ST(0xC1, 0)   # MEM[0xC1]=R0=3
    p.LD(2, 0xC0); p.LD(3, 0xC1)  # R2=9, R3=3
    p.HALT()
    c = run(p)
    check('STI/LD: R2=MEM[0xC0]=9', c.R[2] == 9, f'R2={c.R[2]}')
    check('ST/LD:  R3=MEM[0xC1]=3', c.R[3] == 3, f'R3={c.R[3]}')
    check('RAM[0xC0]=9', c.mem[0xC0] == 9)
    check('RAM[0xC1]=3', c.mem[0xC1] == 3)


# --- D: CALL/RET ---
def test_call_ret():
    p = Asm()
    p.CALL('sub')       # 0x00
    p.MOVI(3, 5)        # 0x02（復帰後）
    p.HALT()            # 0x04
    p.label('sub')
    p.MOVI(2, 7)        # 0x06
    p.RET()             # 0x08
    c = run(p)
    check('CALL/RET: サブR2=7', c.R[2] == 7, f'R2={c.R[2]}')
    check('CALL/RET: 復帰後R3=5', c.R[3] == 5, f'R3={c.R[3]}')
    check('CALL/RET: SP復元=7', c.SP == 7, f'SP={c.SP}')


# --- E: PUSH/POP LIFO（post-dec / pre-inc）---
def test_push_pop():
    p = Asm()
    p.MOVI(0, 3); p.MOVI(1, 6)
    p.PUSH(0); p.PUSH(1)
    p.MOVI(0, 0); p.MOVI(1, 0)
    p.POP(0); p.POP(1)          # LIFO: R0←6, R1←3
    p.HALT()
    c = run(p)
    check('PUSH/POP: R0=6（後入れ先出し）', c.R[0] == 6, f'R0={c.R[0]}')
    check('PUSH/POP: R1=3', c.R[1] == 3, f'R1={c.R[1]}')
    check('PUSH/POP: SP復元=7', c.SP == 7, f'SP={c.SP}')


# --- F: IN/OUT メモリマップド ---
def test_io():
    p = Asm()
    p.IN(0, 1)          # R0←IN[1]
    p.OUT(2, 0)         # OUT[2]←R0
    p.HALT()
    c = TB04CPU(p.assemble())
    c.in_ports[1] = 0xA
    c.run()
    check('IN: R0=IN[1]=0xA', c.R[0] == 0xA, f'R0={c.R[0]}')
    check('OUT: OUT[2]=0xA', c.out_ports[2] == 0xA, f'OUT2={c.out_ports[2]}')
    check('IN: Z更新（0xA→Z=0）', c.Z == 0, f'Z={c.Z}')
    # IN で0を読むと Z=1
    p2 = Asm(); p2.IN(0, 0); p2.HALT()
    c2 = TB04CPU(p2.assemble()); c2.in_ports[0] = 0; c2.run()
    check('IN: 0読み込みで Z=1', c2.Z == 1, f'Z={c2.Z}')


# --- G: CLC/SEC ---
def test_clc_sec():
    p = Asm(); p.SEC(); p.HALT()
    check('SEC: C=1', run(p).C == 1)
    p = Asm(); p.SEC(); p.CLC(); p.HALT()
    check('CLC: C=0', run(p).C == 0)


# --- H: 多倍長加算のゼロ判定（Zin連鎖）---
# ※ 多倍長の最下位ニブル演算は Zin=1 初期化が前提（ドラフト§12-2・未確定の
#   初期化プロトコル）。現状 Z=1 にする専用命令が無いため、ここでは Z=1 を
#   プリセットして初期化プロトコルを代替する。プロトコル確定後は命令列で置換。
def _run_z1(p, **kw):
    c = TB04CPU(p.assemble(), **kw)
    c.Z = 1                      # Zin=1 初期化（プロトコル代替）
    c.run()
    return c


def test_multibyte_zero():
    # 0xFF + 0x01 = 0x100 → 下位8bit=0x00（合成ゼロ）
    p = Asm()
    p.CLC()
    p.MOVI(0, 0xF); p.MOVI(1, 0x1); p.ADD(0, 1)   # 下位 F+1 → 0, C=1, Z=(0&Zin)
    p.MOVI(2, 0xF); p.MOVI(3, 0x0); p.ADD(2, 3)   # 上位 F+0+Cin → 0, C=1
    p.HALT()
    c = _run_z1(p, multi_nibble_z=True)
    check('多倍長 0xFF+1: 下位R0=0', c.R[0] == 0, f'R0={c.R[0]}')
    check('多倍長 0xFF+1: 上位R2=0', c.R[2] == 0, f'R2={c.R[2]}')
    check('多倍長 0xFF+1: 合成Z=1（0x00）', c.Z == 1, f'Z={c.Z}')
    # 非ゼロ側: 0x1F + 0x01 = 0x20（合成非ゼロ）
    p = Asm()
    p.CLC()
    p.MOVI(0, 0xF); p.MOVI(1, 0x1); p.ADD(0, 1)   # 下位 F+1 → 0
    p.MOVI(2, 0x1); p.MOVI(3, 0x0); p.ADD(2, 3)   # 上位 1+0+1 → 2,C=0
    p.HALT()
    c = _run_z1(p, multi_nibble_z=True)
    check('多倍長 0x1F+1: 合成Z=0（0x20）', c.Z == 0, f'Z={c.Z}')


# --- I: SUB/SUBI ボロー連鎖（ADC/SBC）---
def test_sub_borrow():
    # 単発 SUBI は SEC 前置で真の減算: 9-4=5, C=1（ボローなし）
    p = Asm(); p.SEC(); p.MOVI(0, 9); p.SUBI(0, 4); p.HALT()
    c = run(p)
    check('SUBI 9-4=5', c.R[0] == 5, f'R0={c.R[0]}')
    check('SUBI 9-4: C=1（ボローなし）', c.C == 1, f'C={c.C}')
    # 3-5 は借り: y=14(=-2 mod16), C=0（ボロー）
    p = Asm(); p.SEC(); p.MOVI(0, 3); p.SUBI(0, 5); p.HALT()
    c = run(p)
    check('SUBI 3-5: C=0（ボロー発生）', c.C == 0, f'C={c.C}')


# --- J: フェーズ精密モデルと命令単位モデルの一致（4相の妥当性）---
def test_phase_matches_instr():
    progs = {}
    # 算術＋分岐ループ
    p = Asm(); p.MOVI(0, 5)
    p.label('lp'); p.OUT(0, 0); p.SEC(); p.SUBI(0, 1); p.JNZ('lp'); p.HALT()
    progs['countdown'] = p
    # CALL/RET
    p = Asm(); p.CALL('s'); p.MOVI(3, 5); p.HALT()
    p.label('s'); p.MOVI(2, 7); p.RET()
    progs['call'] = p
    # PUSH/POP
    p = Asm(); p.MOVI(0, 3); p.MOVI(1, 6); p.PUSH(0); p.PUSH(1)
    p.MOVI(0, 0); p.MOVI(1, 0); p.POP(0); p.POP(1); p.HALT()
    progs['stack'] = p
    # LD/ST + 論理
    p = Asm(); p.MOVI(0, 0xA); p.ST(0xC0, 0); p.LD(1, 0xC0)
    p.MOVI(2, 0x6); p.AND(1, 2); p.HALT()
    progs['memlogic'] = p

    keys = ('cycle', 'PC', 'SP', 'R', 'C', 'Z', 'OUT', 'IN')
    for name, p in progs.items():
        rom = p.assemble()
        ci = TB04CPU(rom); ci.run(max_instr=300)
        cp = TB04CPUPhase(rom); cp.run(max_instr=300)
        si = ci.state(); sp = cp.core.state()
        same = all(si[k] == sp[k] for k in keys) and ci.mem == cp.core.mem
        detail = '' if same else next(
            f'{k}:{si[k]}!={sp[k]}' for k in keys if si[k] != sp[k])
        check(f'phase≡instr [{name}] 最終状態一致', same, detail)


def main():
    print('=== TB-04 ver2 命令単位シミュレータ 論理検証 ===')
    for t in (test_add_carry, test_compare, test_load_store, test_call_ret,
              test_push_pop, test_io, test_clc_sec, test_multibyte_zero,
              test_sub_borrow, test_phase_matches_instr):
        print(f'\n[{t.__name__}]')
        t()
    print(f'\n=== 結果: {_pass} passed, {_fail} failed ===')
    sys.exit(1 if _fail else 0)


if __name__ == '__main__':
    main()
