
	XOR  R2, R2	; R2 = 0
	MOVI R0, 4
	MOV  R3, R0	; R3 = 4
L0:
	MOVI R0, 1
	ADD  R2, R0
	MOV  R0, R3	; R0 = 4
	XOR  R1, R1	; R1 = 0
L1:
	ADD  R1, R2
	OUT  R1
	SUBI R0, 1
	JZ   L0
	JMP  L1



