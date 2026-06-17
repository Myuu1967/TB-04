"""カウンタプログラム: R0 を 0〜F でループしながら OUT に出力"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from asm import NOP, MOVI, OUTI, OUT, ADDI, JMP

# 0: MOVI R0, 0   R0 = 0
# 1: OUT  R0      OUT ← R0
# 2: ADDI R0, 1   R0 += 1
# 3: JMP  1       → 1 に戻る（0→F でオーバーフロー後また 0 から）
ROM = [
    MOVI(0),    # 0: R0 = 0
    OUT(0),     # 1: OUT ← R0
    ADDI(1),    # 2: R0 += 1
    JMP(1),     # 3: → 1
] + [NOP()] * 12

DESCRIPTION = "R0 を 0〜F でインクリメントし OUT に出力。オーバーフロー後に 0 に戻る。"
