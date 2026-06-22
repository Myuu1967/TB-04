; PRED_PREY — 捕食者(肉食)と被食者(草食)の個体数振動
; 本物のロトカ・ヴォルテラは prey×pred の掛け算が要り4bitでは重い。
; ここは平衡点 K=8 まわりの線形振動子をシンプレクティック更新で解き、
; 軌道が閉じる（周期6）個体数サイクルにした。足し算・引き算だけで成立。
;
;   prey' = prey + (K - pred)     ; 捕食者が少ないと草食が増える
;   pred' = pred + (prey' - K)    ; 草食が多いと肉食が増える（更新後 prey' を使う）
;
; 初期 prey=8, pred=1 → 1〜15 をフルスイング、捕食者が位相遅れで追従。
; レジスタ: R0=作業, R1=prey(草食), R2=pred(肉食)。K は即値8で埋め込み。

	MOVI R0, 8
	MOV  R1, R0	; prey = 8
	MOVI R0, 1
	MOV  R2, R0	; pred = 1
LOOP:
	; --- prey' = prey + 8 - pred ---
	MOV  R0, R1	; R0 = prey
	ADDI R0, 8	; R0 = prey + K
	SUB  R0, R2	; R0 = prey + K - pred
	MOV  R1, R0	; prey 更新
	; --- pred' = pred + prey' - 8 ---
	MOV  R0, R2	; R0 = pred
	ADD  R0, R1	; R0 = pred + prey'
	SUBI R0, 8	; R0 = pred + prey' - K
	MOV  R2, R0	; pred 更新
	OUT  R1		; 草食(prey) を表示
	OUT  R2		; 肉食(pred) を表示
	JMP  LOOP
