; かけ算 四四（4×4）全組み合わせ — 足し算の繰り返しで生成
; i=1..4 について i,2i,3i,4i を順に OUT（全16積を出力）
; レジスタ: R0=作業/内側カウンタ k, R1=積 acc, R2=被乗数 i, R3=定数4
; 終了判定: 4×4=16 が4bitで 0 になり Z=1 が立つのを利用してハルト
;          （外側カウンタ不要＝レジスタ4本に収まる）

	XOR  R2, R2	; R2 = 0   (i)
	MOVI R0, 4
	MOV  R3, R0	; R3 = 4   (内側ループ回数の定数)
L0:
	MOVI R0, 1
	ADD  R2, R0	; i += 1   (R2 = 1,2,3,4)
	MOV  R0, R3	; R0 = 4   (内側カウンタ k)
	XOR  R1, R1	; acc = 0
L1:
	ADD  R1, R2	; acc += i
	OUT  R1		; OUT ← acc  (i, 2i, 3i, 4i)
	SUBI R0, 1	; k -= 1
	JZ   ENDROW	; k==0 なら 1 行終了
	JMP  L1
ENDROW:
	OR   R1, R1	; Z = (acc==0)  ← i=4 で acc=16→0
	JZ   HALT	; 4×4 まで出したら停止
	JMP  L0		; 次の i へ
HALT:
	JMP  HALT	; 無限ループ（停止）
