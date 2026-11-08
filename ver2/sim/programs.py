"""TB-04 ver2 デモプログラム集（ver1 codes/ の主要デモを ver2 へ移植）

各関数は (Asm, 説明) を返す。ver1 との差の要点:
  - ver1 の ADD/SUB/ADDI/SUBI は Cin なしの素の演算。ver2 は ADC/SBC
    （ADD=a+b+Cin, SUB=a-b-1+Cin）なので、素の加算前に CLC(C=0)、
    素の減算前に SEC(C=1) を置いて移植する（ドラフト§12-4）。
  - OUT は ver2 のポート0を使用（ver1 の単一 OUT ポート相当）。
  - IN は ver2 のポート0。MOVI/ADDI/SUBI は任意 Ri を取れる。
"""
from asm import Asm


def counter():
    """IN で方向選択（0=カウントダウン / 非0=カウントアップ）。ver1 counter.asm 相当。"""
    p = Asm()
    p.IN(0, 0)
    p.JZ('down')          # IN==0 → カウントダウン
    p.MOVI(0, 0)
    p.label('up')
    p.CLC(); p.ADDI(0, 1); p.OUT(0, 0); p.JMP('up')     # 0→F 巡回
    p.label('down')
    p.SEC(); p.SUBI(0, 1); p.OUT(0, 0); p.JMP('down')   # F→0 巡回
    return p, 'カウンタ（IN=0でダウン/非0でアップ・0-F巡回）'


def led_flow():
    """流れるLED。IN で2パターン切替。ver1 LED_FLOW.ASM 相当。"""
    p = Asm()
    p.IN(0, 0)
    p.JZ('patB')
    p.label('patA')
    for v in (0b0011, 0b0110, 0b1100, 0b1000):
        p.OUTI(0, v)
    p.JMP('patA')
    p.label('patB')
    for v in (0b0001, 0b0011, 0b0110, 0b1100, 0b1000, 0b1100, 0b0110, 0b0011):
        p.OUTI(0, v)
    p.JMP('patB')
    return p, '流れるLED（OUTIパターン列・INで2種切替）'


def fibonacci():
    """フィボナッチ数列 mod 16。ver1 FIBONACCI.ASM 相当。"""
    p = Asm()
    p.MOVI(0, 1); p.MOV(1, 0); p.MOVI(0, 0)   # R0=0, R1=1
    p.label('L1')
    p.XOR(2, 2)                 # R2 = 0
    p.CLC(); p.ADD(2, 0)        # R2 += R0（素の加算）
    p.CLC(); p.ADD(2, 1)        # R2 += R1
    p.OUT(0, 2)
    p.MOV(0, 1); p.MOV(1, 2)    # 桁送り
    p.JMP('L1')
    return p, 'フィボナッチ数列 mod16（ピサノ周期24）'


def ramen_timer():
    """遅延ループ式タイマー（OUTIで段階表示）。ver1 RAMEN_TIMER.ASM 相当。"""
    p = Asm()
    p.OUTI(0, 1)                # 開始
    def delay(lbl):             # R0 を16回インクリメント＝1単位待ち（C=1で抜ける）
        p.label(lbl)
        p.CLC(); p.ADDI(0, 1); p.JNC(lbl)
    delay('t0'); delay('t1')
    p.OUTI(0, 3)
    delay('t2'); delay('t3')
    p.label('t4')               # 点滅しながら待つ
    p.OUTI(0, 0); p.OUTI(0, 7)
    p.CLC(); p.ADDI(0, 1); p.JNC('t4')
    p.OUTI(0, 15)               # 完了
    p.HALT()
    return p, 'ラーメンタイマー（遅延ループ・段階OUTI・完了でHALT）'


def kakezan():
    """4×4 かけ算表（加算の繰り返しで全16積を OUT）。ver1 KAKEZAN_44.ASM 相当。"""
    p = Asm()
    p.XOR(2, 2)                 # R2 = i = 0
    p.MOVI(0, 4); p.MOV(3, 0)   # R3 = 4（内側回数）
    p.label('L0')
    p.MOVI(0, 1); p.CLC(); p.ADD(2, 0)   # i += 1
    p.MOV(0, 3)                 # k = 4
    p.XOR(1, 1)                 # acc = 0
    p.label('L1')
    p.CLC(); p.ADD(1, 2)        # acc += i
    p.OUT(0, 1)                 # i, 2i, 3i, 4i
    p.SEC(); p.SUBI(0, 1)       # k -= 1
    p.JZ('endrow')
    p.JMP('L1')
    p.label('endrow')
    p.OR(1, 1)                  # Z = (acc==0)  ← i=4 で 16→0
    p.JZ('done')
    p.JMP('L0')
    p.label('done')
    p.HALT()
    return p, '4×4かけ算表（i,2i,3i,4i を OUT・16=0で停止）'


def life_ca():
    """4LED 1次元セルオートマトン（Rule60＋帰還・周期15）。ver1 LIFE_CA.ASM 相当。"""
    p = Asm()
    p.MOVI(0, 1); p.MOV(1, 0)   # 状態 = 0001
    p.MOVI(0, 3); p.MOV(2, 0)   # 帰還タップ = 0b0011
    p.MOVI(0, 7); p.MOV(3, 0)   # 入力マスク = 0b0111
    p.label('loop')
    p.OUT(0, 1)                 # 現世代
    p.IN(0, 0); p.AND(0, 3)     # 入力を下位3bitにマスク
    p.OR(1, 0)                  # 点灯セル注入
    p.CLC(); p.ADD(1, 1)        # 左シフト（=2倍）。C=あふれ最上位
    p.JNC('skip')
    p.XOR(1, 2)                 # 帰還：state ^= タップ
    p.label('skip')
    p.JMP('loop')
    return p, 'ライフゲーム風1次元CA（Rule60＋帰還・周期15）'


def pred_prey():
    """捕食被食の個体数振動（線形振動子・周期6）。ver1 PRED_PREY.ASM 相当。"""
    p = Asm()
    p.MOVI(0, 8); p.MOV(1, 0)   # prey = 8
    p.MOVI(0, 1); p.MOV(2, 0)   # pred = 1
    p.label('loop')
    # prey' = prey + 8 - pred
    p.MOV(0, 1); p.CLC(); p.ADDI(0, 8); p.SEC(); p.SUB(0, 2); p.MOV(1, 0)
    # pred' = pred + prey' - 8
    p.MOV(0, 2); p.CLC(); p.ADD(0, 1); p.SEC(); p.SUBI(0, 8); p.MOV(2, 0)
    p.OUT(0, 1)                 # 草食(prey)
    p.OUT(0, 2)                 # 肉食(pred)
    p.JMP('loop')
    return p, '捕食被食の個体数振動（prey/pred交互OUT・周期6）'


def calc():
    """2桁(8bit)の加減算電卓。ver2のCin付きADD/SUB＋フラグ保持のショーケース。

    IN  p0=値の下位ニブル / p1=上位ニブル / p2=コマンド
        （1=Aへ取込, 2=Bへ取込, 3=A+B, 4=A-B, 0=待機）
    OUT p0=結果の下位 / p1=上位 / p2=C（加算は桁上がり, 減算は1=借りなし）
    RAM 0xC0-C1=A（下位,上位） 0xC2-C3=B
    """
    p = Asm()
    p.label('main')
    p.IN(7, 2); p.JZ('main')                 # INはZを更新＝コマンド0なら待機
    p.MOVI(6, 1); p.SEC(); p.CP(7, 6); p.JZ('getA')
    p.MOVI(6, 2); p.SEC(); p.CP(7, 6); p.JZ('getB')
    p.MOVI(6, 3); p.SEC(); p.CP(7, 6); p.JZ('doAdd')
    p.MOVI(6, 4); p.SEC(); p.CP(7, 6); p.JZ('doSub')
    p.JMP('main')
    p.label('getA')
    p.IN(0, 0); p.IN(1, 1); p.ST(0xC0, 0); p.ST(0xC1, 1); p.JMP('echo')
    p.label('getB')
    p.IN(0, 0); p.IN(1, 1); p.ST(0xC2, 0); p.ST(0xC3, 1); p.JMP('echo')
    p.label('doAdd')                          # 下位のCoutが上位のCinへ自動で伝わる
    p.CLC()
    p.LD(0, 0xC0); p.LD(2, 0xC2); p.ADD(0, 2)
    p.LD(1, 0xC1); p.LD(3, 0xC3); p.ADD(1, 3); p.JMP('show')
    p.label('doSub')                          # 減算は SEC（借りなし）から始める
    p.SEC()
    p.LD(0, 0xC0); p.LD(2, 0xC2); p.SUB(0, 2)
    p.LD(1, 0xC1); p.LD(3, 0xC3); p.SUB(1, 3); p.JMP('show')
    p.label('echo')
    p.OUT(0, 0); p.OUT(1, 1); p.JMP('wait0')
    p.label('show')
    p.OUT(0, 0); p.OUT(1, 1)                  # OUT/MOVI は C を保持するので後で拾える
    p.MOVI(4, 0); p.JNC('nc'); p.MOVI(4, 1)
    p.label('nc')
    p.OUT(2, 4)
    p.label('wait0')
    p.IN(7, 2); p.JNZ('wait0'); p.JMP('main')  # コマンドが0に戻るまで待つ
    return p, '2桁(8bit)加減算電卓（IN p2=1:Aへ 2:Bへ 3:加算 4:減算／OUT p2=C）'


def sec_count():
    """1秒ごとに OUT[0] をカウントアップ。**1kHz設定（=1024Hz）専用**。

    1命令=4クロックなので 1024/4 = 256命令 がちょうど1秒。
    ループ1周を 256命令 に合わせてある（外10回×内11回＋前後6命令）。
    内側が SUBI+JNZ の2命令で回るのは、借りが出ない限り SUBI 自身が
    C=1 を残すため（SEC はループの外で1回だけでよい）。
    ※4Hz/32Hz に切り替えると1周が256秒/32秒になる。
    """
    p = Asm()
    p.XOR(5, 5)                     # R5 = 表示カウンタ
    p.label('loop')
    p.OUT(0, 5)
    p.CLC(); p.ADDI(5, 1)           # R5 += 1（0-F巡回）
    p.MOVI(1, 10); p.SEC()          # 外側10回。SEC はここ1回だけ
    p.label('outer')
    p.MOVI(0, 11)                   # 内側11回
    p.label('inner')
    p.SUBI(0, 1); p.JNZ('inner')
    p.SUBI(1, 1); p.JNZ('outer')
    p.JMP('loop')
    return p, '1秒ごとにOUTをカウントアップ（1kHz=1024Hz前提・1周ちょうど256命令）'


def showcase():
    """展示用デモ（30秒動画向け）。命令表示4桁に単語→OUT 2×2で10進4桁カウンタ。

    単語は命令そのものを OPC・OPR1・OPR2・OPR3（=byte1上/下・byte2上/下）に見せる。
    先頭ニブル6-Dは未定義＝デコーダROMがNOP_SAFEを出すので何も起きない。
    0x20xx(MOVI)・0x11xx(MOV)は R2 を 0 にするだけ（R0-R3はリセットで0）。
    単語が読めるのは4Hz（1命令=1秒）のときだけ。
    OUTの配置＝上段 OUT2 OUT3／下段 OUT0 OUT1 ＝ 千 百／十 一。
    1kHzでは1カウント約6命令＝約40カウント/秒。
    """
    p = Asm()
    for port in range(4):
        p.OUTI(port, 0)               # OUTはリセットで不定
    for b1, b2 in ((0xC0, 0xDE), (0xCA, 0xFE), (0x20, 0x26), (0x11, 0x28)):
        p.DATA(b1, b2)                # C0DE / CAFE / 2026 / 1128
    p.MOVI(7, 9)
    # ADDI 直後は C=0 なので CP Ri,R7 は Ri-9-1 ＝ Ri==10 で Z=1
    p.label('loop')
    p.CLC(); p.ADDI(0, 1); p.CP(0, 7); p.JNZ('d0')
    p.MOVI(0, 0); p.OUT(1, 0)
    p.CLC(); p.ADDI(1, 1); p.CP(1, 7); p.JNZ('d1')
    p.MOVI(1, 0); p.OUT(0, 1)
    p.CLC(); p.ADDI(2, 1); p.CP(2, 7); p.JNZ('d2')
    p.MOVI(2, 0); p.OUT(3, 2)
    p.CLC(); p.ADDI(3, 1); p.CP(3, 7); p.JNZ('d3')
    p.MOVI(3, 0)
    p.label('d3'); p.OUT(2, 3); p.JMP('loop')
    p.label('d2'); p.OUT(3, 2); p.JMP('loop')
    p.label('d1'); p.OUT(0, 1); p.JMP('loop')
    p.label('d0'); p.OUT(1, 0); p.JMP('loop')
    return p, '展示用（命令表示に単語→OUT 2×2で10進4桁カウンタ）'


PROGRAMS = {
    'counter': counter,
    'led_flow': led_flow,
    'fibonacci': fibonacci,
    'ramen_timer': ramen_timer,
    'kakezan': kakezan,
    'life_ca': life_ca,
    'pred_prey': pred_prey,
    'calc': calc,
    'sec_count': sec_count,
    'showcase': showcase,
}
