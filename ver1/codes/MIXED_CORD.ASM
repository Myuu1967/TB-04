; LED FLOW

	IN   R0
	JZ   L1
L0:
	OUTI 3
	OUTI 6
	OUTI 12
	OUTI 8
	JMP  L0

L1:
	OUTI 1
	OUTI 3
	OUTI 6
	OUTI 12
	OUTI 8
	OUTI 12
	OUTI 6
	OUTI 3
	JMP  L1

    .org  0x20

; Counter

	IN   R0
	JZ   L1
	MOVI R0, 0
L0:
	ADDI R0, 1
	OUT  R0
	JMP  L0
L1:
	SUBI R0, 1
	OUT  R0
	JMP  L1


    .org  0x40

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

    .org  0x60

; TASHIZAN 4 4

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


    .org  0x80

; LIFE_CA — 4LED上で“生きている”1次元セルオートマトン（自己再生型）
; 4セルだけの純CAは全滅(→0)するため、あふれビットを帰還させて消えない
; 4bit最大長LFSR(周期15)にした「Rule60＋帰還」。IN でセルを注入できる。
;
; 1世代の更新:
;   注入  : R1 |= (IN & 0b0111)        ; AND でマスク → OR で点灯セル注入
;   CA一歩: R1 <<= 1 (ADD R1,R1)       ; 左隣へずらす。C=あふれた最上位
;   帰還  : C==1 なら R1 ^= 0b0011      ; XOR タップ（これで消えず巡回）
;
; レジスタ: R0=作業/入力, R1=状態(4セル), R2=帰還タップ(0b0011), R3=入力マスク(0b0111)

	MOVI R0, 1
	MOV  R1, R0	; 状態 = 0001（種：1セル点灯）
	MOVI R0, 3
	MOV  R2, R0	; R2 = 帰還タップ M = 0b0011
	MOVI R0, 7
	MOV  R3, R0	; R3 = 入力マスク = 0b0111
LOOP:
	OUT  R1		; 現世代を LED へ
	IN   R0		; ボタン/DIP 入力
	AND  R0, R3	; 入力を下位3bitにマスク（AND）
	OR   R1, R0	; 点灯セルを注入（OR）
	ADD  R1, R1	; 左シフト＝CA一歩。C = あふれた最上位
	JNC  L2		; あふれ無し → 帰還しない
	XOR  R1, R2	; 帰還：state ^= タップ（XOR）
L2:
	JMP  LOOP	; 次世代へ


    .org  0xA0

; RAMEN TIMER

	OUTI 1

L0:
	ADDI R0, 1
	JNC  L0

L1:
	ADDI R0, 1
	JNC  L1

	OUTI 3
L2:
	ADDI R0, 1
	JNC  L2

L3:
	ADDI R0, 1
	JNC  L3

L4:
	OUTI 0
	OUTI 7
	ADDI R0, 1
	JNC  L4


	OUTI 15
L5:
	JMP  L5


    .org  0xC0

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


