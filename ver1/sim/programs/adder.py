"""加算デモ: R0=5, R1=3 を ADD して OUT に出力。JNC で結果確認。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from asm import NOP, MOVI, MOV, ADD, ADDI, SUB, SUBI, OUT, OUTI, JMP, JNC, JZ

# MOVI は R0 のみ直接ロード可能。他レジスタは MOVI→MOV で設定。
#
# 0: MOVI R0, 5    R0 = 5
# 1: MOV  R1, R0   R1 = R0 = 5
# 2: MOVI R0, 3    R0 = 3
# 3: ADD  R1, R0   R1 = R1 + R0 = 5 + 3 = 8, C=0, Z=0
# 4: OUT  R1       OUT = 8
# 5: MOVI R0, 9    R0 = 9
# 6: ADDI R0, 9    R0 = 9 + 9 = 18 → R0 = 2, C=1 (オーバーフロー)
# 7: OUT  R0       OUT = 2
# 8: JNC  0xA      C==0 なら 0xA へ（ここでは C==1 なので通過）
# 9: OUTI 0xF      C==1 の表示: OUT = F
# A: JMP  0xA      無限ループ（halt 代わり）
# B〜F: NOP

ROM = [
    MOVI(5),        # 0
    MOV(1, 0),      # 1: R1 = R0
    MOVI(3),        # 2: R0 = 3
    ADD(1, 0),      # 3: R1 = R1 + R0 = 8
    OUT(1),         # 4: OUT = 8
    MOVI(9),        # 5: R0 = 9
    ADDI(9),        # 6: R0 = 9+9=18 → R0=2, C=1
    OUT(0),         # 7: OUT = 2
    JNC(0xA),       # 8: C==0 なら 0xA へ（ここでは飛ばない）
    OUTI(0xF),      # 9: C==1 の証拠 → OUT = F
    JMP(0xA),       # A: 無限ループ
] + [NOP()] * 5

DESCRIPTION = "5+3=8 を出力、9+9=18（オーバーフロー）で C=1 を JNC で確認。"
