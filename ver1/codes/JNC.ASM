    MOVI R0, 15
    MOV R1, R0
    XOR R0, R0
L1:
    ADDI R0, 1
    JNC  L1
    MOVI R0, 15
L2:
    SUBI R0, 1
    JZ   L3
    JMP  L2
L3:
    XOR  R0, R1
    OUT  R0
    JMP  L3
