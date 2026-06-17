;フィボナッチ数列の計算（モード16）
; An+1 = An + An-1 (A1 = 1, A0 = 0)
;
    MOVI R0, 1
    MOV  R1, R0
    MOVI R0, 0
L1:
    XOR  R2, R2
    ADD  R2, R0
    ADD  R2, R1
    OUT  R2
    MOV  R0, R1
    MOV  R1, R2
    JMP  L1