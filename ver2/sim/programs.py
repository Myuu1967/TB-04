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


def hanoi():
    """ハノイの塔4枚（CALL/RET の再帰）。棒0・1・2＝OUT0・OUT1・OUT3（OUT2は常に0）。

    棒の表示は積み上げ式＝載っている枚数だけ bit0（いちばん下）から点ける（4枚=F 3枚=7 2枚=3 1枚=1）。
    円盤の大きさは表示しない。解き終えたら少し待って、逆向きにもう一度解く（くり返し）。
    引数はスタックに積まない（スタックは戻り番地だけ・深さ＝枚数）:
      棒の番号はワンホット（1/2/4）で R1=移動元・R2=移動先・R3=作業用。
      再帰の前にレジスタを入れ替えてCALLし、戻ったら入れ替え直す。
      R4＝円盤のマスク。ROR で1段小さく、ROL で元に戻す（SHR だと1→0で情報が消える）。
    移動＝移動元の棒を SHR（1枚減る）、移動先の棒を SEC＋ADD x,x（2x+1＝1枚増える）。
    R0=作業 R5-R7=棒0-2 RAM 0xC1=待ちの外側カウンタ
    クロック目安＝512Hz（1手約1秒）。
    """
    p = Asm()
    p.MOVI(1, 1); p.MOVI(2, 4); p.MOVI(3, 2)     # 棒0→棒2（作業用は棒1）
    p.MOVI(5, 0xF); p.MOVI(6, 0); p.MOVI(7, 0)
    p.OUT(0, 5); p.OUT(1, 6); p.OUTI(2, 0); p.OUT(3, 7)
    p.label('main')
    p.MOVI(4, 8)                                  # いちばん大きい円盤から
    p.CALL('delay')
    p.CALL('hanoi')
    p.CALL('delay'); p.CALL('delay')
    p.MOV(0, 1); p.MOV(1, 2); p.MOV(2, 0)         # 移動元と移動先を入れ替えて逆向きに
    p.JMP('main')

    p.label('hanoi')                              # hanoi(R4, R1→R2, 作業R3)
    p.MOV(0, 4); p.SHR(0); p.JZ('move')           # いちばん小さい円盤＝動かすだけ
    p.ROR(4)
    p.MOV(0, 2); p.MOV(2, 3); p.MOV(3, 0)         # 移動先⇔作業用
    p.CALL('hanoi')                               # 上の山を作業用へ
    p.MOV(0, 2); p.MOV(2, 3); p.MOV(3, 0)
    p.ROL(4)
    p.CALL('move')                                # この円盤を移動先へ
    p.ROR(4)
    p.MOV(0, 1); p.MOV(1, 3); p.MOV(3, 0)         # 移動元⇔作業用
    p.CALL('hanoi')                               # 上の山を移動先へ
    p.MOV(0, 1); p.MOV(1, 3); p.MOV(3, 0)
    p.ROL(4)
    p.RET()

    p.label('move')                               # 一番上の1枚を R1 から R2 へ
    p.MOV(0, 1)                                   # 移動元：1枚減らす
    p.SHR(0); p.JNC('s1'); p.SHR(5); p.OUT(0, 5); p.JMP('dst')
    p.label('s1')
    p.SHR(0); p.JNC('s2'); p.SHR(6); p.OUT(1, 6); p.JMP('dst')
    p.label('s2')
    p.SHR(7); p.OUT(3, 7)
    p.label('dst')
    p.MOV(0, 2)                                   # 移動先：1枚増やす（2x+1）
    p.SHR(0); p.JNC('t1'); p.SEC(); p.ADD(5, 5); p.OUT(0, 5); p.JMP('delay')
    p.label('t1')
    p.SHR(0); p.JNC('t2'); p.SEC(); p.ADD(6, 6); p.OUT(1, 6); p.JMP('delay')
    p.label('t2')
    p.SEC(); p.ADD(7, 7); p.OUT(3, 7)
    # ↓そのまま delay へ落ちて RET する

    p.label('delay')                              # 約130命令（512Hzで約1秒）
    p.STI(0xC1, 4)
    p.label('d1')
    p.MOVI(0, 0); p.CLC()
    p.label('d0')
    p.ADDI(0, 1); p.JNC('d0')                     # 16回
    p.LD(0, 0xC1); p.SEC(); p.SUBI(0, 1); p.ST(0xC1, 0); p.JNZ('d1')
    p.RET()
    return p, 'ハノイの塔4枚（CALL/RET再帰・棒=OUT0-2・OUT3=手数・512Hz目安）'


def ishitori():
    """石取りゲーム（1回に1〜3個・最後の1個を取ったら勝ち）。CPUは4の倍数を残す必勝法。

    キーパッド（IN0＝コード・IN1 bit0＝DA。押して離すと1回）: 1/2/3＝その数だけ取る・F(C)＝新しいゲーム・
    ほかのキーは無視。
    リセット後はどれかのキーで開始。石の数は 8〜15（キー待ちの間に回すカウンタで決まる）。
    8・12 で始まると人は必ず負け、それ以外は正しく取れば人が勝てる。
    表示: 下段 OUT0・OUT1＝残りの石（10進2桁）／上段 OUT2＝あなたが取った数・OUT3＝CPU。
    勝った側の上段が点滅し、どれかのキーで次のゲーム。残りより多くは取れない（無視）。
    R1=石 R2=乱数カウンタ R3=DA R4=キーコード（取る数） R0=作業 RAM 0xC1=待ちの外側カウンタ
    クロック目安＝1024Hz。
    """
    p = Asm()
    for port in range(4):
        p.OUTI(port, 0)
    p.label('w0')                                 # どれかのキーで開始
    p.CLC(); p.ADDI(2, 1); p.IN(0, 1); p.JZ('w0')
    p.label('new')
    p.IN(0, 1); p.JNZ('new')                      # 離すのを待つ
    p.OUTI(2, 0); p.OUTI(3, 0)
    p.MOVI(0, 7); p.MOV(1, 2); p.AND(1, 0)
    p.MOVI(0, 8); p.OR(1, 0)                      # 石 = 8〜15
    p.CALL('show')

    p.label('human')
    p.CLC(); p.ADDI(2, 1); p.IN(0, 1); p.JZ('human')
    p.label('h2')
    p.IN(0, 1); p.JNZ('h2')
    p.IN(4, 0)                                    # キーコード＝取る数
    p.MOVI(0, 15); p.SEC(); p.CP(4, 0); p.JZ('new')   # F(C)＝新しいゲーム
    p.MOV(0, 4); p.SEC(); p.SUBI(0, 1); p.JNC('human')   # 0 は無視
    p.SUBI(0, 3); p.JC('human')                   # 4 以上は無視
    p.SEC(); p.CP(1, 4); p.JNC('human')           # 残りより多い＝無視
    p.SEC(); p.SUB(1, 4); p.OUT(2, 4); p.CALL('show')
    p.OR(1, 1); p.JZ('hwin')
    p.CALL('delay')                               # CPU が考えるふり
    p.MOVI(0, 3); p.MOV(4, 1); p.AND(4, 0); p.JNZ('ctake')   # 石 mod 4 を取る
    p.MOVI(4, 1)                                  # 4の倍数なら1個（負け筋）
    p.label('ctake')
    p.SEC(); p.SUB(1, 4); p.OUT(3, 4); p.CALL('show')
    p.OR(1, 1); p.JZ('cwin')
    p.JMP('human')

    p.label('hwin')                               # あなたの勝ち＝OUT2 が点滅
    p.OUTI(2, 15); p.CALL('delay'); p.OUTI(2, 0); p.CALL('delay')
    p.OR(3, 3); p.JZ('hwin'); p.JMP('new')
    p.label('cwin')                               # CPU の勝ち＝OUT3 が点滅
    p.OUTI(3, 15); p.CALL('delay'); p.OUTI(3, 0); p.CALL('delay')
    p.OR(3, 3); p.JZ('cwin'); p.JMP('new')

    p.label('show')                               # 石を10進2桁で表示
    p.MOV(0, 1); p.SEC(); p.SUBI(0, 10); p.JNC('lt10')
    p.OUTI(0, 1); p.OUT(1, 0); p.RET()
    p.label('lt10')
    p.OUTI(0, 0); p.OUT(1, 1); p.RET()

    p.label('delay')                              # 約200命令。キーが押されたら抜ける（R3=DA）
    p.STI(0xC1, 3)
    p.label('d1')
    p.MOVI(0, 0); p.CLC()
    p.label('d0')
    p.IN(3, 1); p.JNZ('dret'); p.ADDI(0, 1); p.JNC('d0')
    p.LD(0, 0xC1); p.SEC(); p.SUBI(0, 1); p.ST(0xC1, 0); p.JNZ('d1')
    p.label('dret')
    p.RET()
    return p, '石取り（1〜3個・最後を取ったら勝ち・CPUは4の倍数を残す／キー 1/2/3＝取る数・F＝新ゲーム）'


def kaprekar():
    """カプレカ数 6174。4桁を「大きい順−小さい順」でくり返すと7回以内に6174に着く。

    入力＝キーパッド（IN0＝コード・IN1 bit0＝DA）。数字キー 0〜9 で右から1桁ずつ入れ（4桁打つ）、
    A〜F（E＝「＝」を推奨）で計算を始める。表示＝上段 OUT2 OUT3／下段 OUT0 OUT1＝千 百／十 一。
      いまの数 → 大きい順に並べた数 → 引き算の結果 … 6174 を表示したまま次の入力を待つ。
    計算中はキーを押している間だけ待ちを飛ばす（早送り）。
    全桁が同じ数（1111等）は 0 になるので進まない（入力待ちに戻る）。
    並べ替え＝比較交換5回の固定ネットワーク（配列不要）。CP は Cin を使うが、
      C=0 なら「>」・C=1 なら「≧」になるだけで、どちらでも並べ替えは正しい＝SEC 不要。
    引き算＝10進の桁ごと（借りが出たら +10。ADDI で C が立つので CLC で借りに戻す）。
    6174 の判定は千=6・百=1 の2桁で足りる（途中に出る値をすべて調べて確認）。
    待ちはキー（DA）で抜け、Z=0 で戻る（ふつうに終われば Z=1。RET はフラグを変えない）。
    R4-R7＝千 百 十 一  R0-R2＝作業  クロック目安＝1024Hz。
    """
    p = Asm()
    p.label('entry')                              # 入力待ち
    p.CALL('show'); p.JZ('entry')                 # キーなしなら表示し直す
    p.label('kr')
    p.IN(0, 1); p.JNZ('kr')                       # 離すのを待つ
    p.IN(0, 0); p.MOV(1, 0); p.SEC(); p.SUBI(1, 10); p.JC('loop')   # A〜F＝開始
    p.MOV(4, 5); p.MOV(5, 6); p.MOV(6, 7); p.MOV(7, 0); p.JMP('entry')
    p.label('loop')
    p.CALL('show')
    for a, b in ((4, 5), (6, 7), (4, 6), (5, 7), (5, 6)):   # 大きい順に並べる
        p.CP(a, b); p.JC(f's{a}{b}')
        p.MOV(0, a); p.MOV(a, b); p.MOV(b, 0)
        p.label(f's{a}{b}')
    p.SEC(); p.CP(4, 7); p.JZ('entry')                       # 全桁同じ
    p.CALL('show')
    # 大きい順(R4R5R6R7) − 小さい順(R7R6R5R4)
    p.MOV(1, 7); p.SEC(); p.SUB(1, 4); p.JC('b1')
    p.CLC(); p.ADDI(1, 10); p.CLC()
    p.label('b1')
    p.MOV(2, 6); p.SUB(2, 5); p.JC('b2')
    p.CLC(); p.ADDI(2, 10); p.CLC()
    p.label('b2')
    p.MOV(3, 5); p.SUB(3, 6); p.JC('b3')
    p.CLC(); p.ADDI(3, 10); p.CLC()
    p.label('b3')
    p.MOV(0, 4); p.SUB(0, 7)
    p.MOV(4, 0); p.MOV(5, 3); p.MOV(6, 2); p.MOV(7, 1)
    p.MOVI(0, 6); p.SEC(); p.CP(4, 0); p.JNZ('loop')         # 6174 か
    p.MOVI(0, 1); p.CP(5, 0); p.JNZ('loop')
    p.JMP('entry')                                           # 6174 を出したまま入力待ち

    p.label('show')                               # 4桁を出して約1秒待つ（キーで抜ける）
    p.OUT(2, 4); p.OUT(3, 5); p.OUT(0, 6); p.OUT(1, 7)
    p.MOVI(1, 4)
    p.label('d0')                                 # 内側は R0 の桁あふれまで（初期値は問わない）
    p.IN(2, 1); p.JNZ('dret'); p.ADDI(0, 1); p.JNC('d0')
    p.SUBI(1, 1); p.JNZ('d0')                     # 抜けたとき C=1 なので SEC 不要
    p.label('dret')
    p.RET()
    return p, 'カプレカ数6174（キーで4桁→A〜Fで開始・大きい順−小さい順をくり返す）'


def rule_ca():
    """16セルの1次元セルオートマトン（環状）。Rule90（シェルピンスキー）と Rule30（カオス）。

    16セル＝R4 R5 R6 R7（R4が上位）。表示＝OUT2 OUT3 OUT0 OUT1（上段左→下段右の読み順・
    各ポートは bit3 が左のつもり）。※LED の物理的な並びは未確認。
    Rule90: 新 = 左 ^ 右       Rule30: 新 = 左 ^ (自分 | 右)
    左回転＝4ニブルを ADD の桁上げで連鎖させ、あふれを ADDI x,0 で最下位へ戻す（6命令）。
    右回転＝左回転を15回（この繰り返しが1世代の待ち時間も兼ねる。1024Hzで約0.8秒/世代）。
    Rule90 は単一セルから8世代で全部消える（16=2^4 の環の性質）→ 中央に種をまき直す。
    キーパッド（押して離す）: 8〜F＝Rule90で最初から（9 を押す）／0〜7＝Rule30で最初から（3 を押す）。
    判定はコードの bit3（ADD x,x の桁上げ）。リセット後は Rule90。
    R0-R3＝作業（回転中のコピー） RAM 0xC2＝規則（0=90/1=30） 0xC4-C7＝世代 0xC8-CB＝左隣
    """
    p = Asm()
    p.STI(0xC2, 0)
    p.label('seed')
    p.MOVI(4, 0); p.MOVI(5, 0); p.MOVI(6, 8); p.MOVI(7, 0)   # 中央に1セル

    def rotl():
        p.CLC(); p.ADD(3, 3); p.ADD(2, 2); p.ADD(1, 1); p.ADD(0, 0); p.ADDI(3, 0)

    p.label('gen')
    p.OUT(2, 4); p.OUT(3, 5); p.OUT(0, 6); p.OUT(1, 7)
    for k in range(4):
        p.MOV(k, 4 + k)
    rotl()
    for k in range(4):
        p.PUSH(k)                                 # 左回転＝各セルの右隣（上位が左）
    for k in range(4):
        p.ST(0xC4 + k, 4 + k)                     # 今の世代を退避（R4-R7 を空ける）
    p.MOVI(4, 14)
    p.label('rr')                                 # さらに14回＝合計15回＝右回転＝左隣
    rotl()
    p.IN(5, 1); p.JNZ('key')                      # DA
    p.SEC(); p.SUBI(4, 1); p.JNZ('rr')
    for k in range(4):
        p.ST(0xC8 + k, k)                         # 左隣を退避
    for k in (3, 2, 1, 0):
        p.POP(k)                                  # R0-R3 = 右隣
    p.LD(5, 0xC2); p.OR(5, 5); p.JZ('r90')
    for k in range(4):                            # Rule30: 右 |= 自分
        p.LD(4 + k, 0xC4 + k); p.OR(k, 4 + k)
    p.label('r90')
    for k in range(4):                            # 新 = 左 ^ (右 か 自分|右)
        p.LD(4 + k, 0xC8 + k); p.XOR(4 + k, k)
    p.MOV(0, 4); p.OR(0, 5); p.OR(0, 6); p.OR(0, 7)
    p.JZ('seed')                                  # 全部消えたら種をまき直す
    p.JMP('gen')

    p.label('key')
    for k in range(4):
        p.POP(0)                                  # 積んだ4個を捨てる
    p.label('kr')
    p.IN(0, 1); p.JNZ('kr')                       # 離すのを待つ
    p.IN(5, 0)
    p.STI(0xC2, 0); p.ADD(5, 5); p.JC('seed')     # bit3=1（8〜F）＝Rule90
    p.STI(0xC2, 1); p.JMP('seed')                 # 0〜7＝Rule30
    return p, '16セル1次元CA（Rule90/Rule30・環状／キー 9=Rule90 3=Rule30）'


def collatz():
    """コラッツの 3n+1（16bit）。偶数なら ÷2、奇数なら 3n+1 をくり返すと 1 に着く。

    入力＝キーパッド（IN0＝コード・IN1 bit0＝DA）。キー 0〜F を押すたびに、その桁を右から入れた
    新しい値で最初からやり直す（4桁打てば好きな値。決定キーは要らない）。リセット直後は 27。
    表示＝いまの値を16進4桁（上段 OUT2 OUT3／下段 OUT0 OUT1）。1に着いたら手数を16進で
    表示して次のキーを待つ。27 は 111手（006F）・最大 9232（2410）。16bit をあふれたら EEEE。
    0 を入れると 0 のまま回り続ける（キーでやり直す）。
    ÷2＝下の桁から SHR し、上の桁の最下位を下の桁の bit3 へ入れる。
      C=1 のとき ADDI x,7 は 7+Cin=8 を足す＝bit3 を立てる。
    3n+1＝n に n を2回足す（2回目は SEC で +1 を兼ねる）。桁上げは ADD の Cin で連鎖。
    待ちはキー（DA）で抜け、Z=0 で戻る（ふつうに終われば Z=1。RET はフラグを変えない）。
    R4-R7＝n（R4が上位） R0-R3＝作業 RAM 0xC0-C1＝手数（下位・上位） 0xC5-C7＝入力の下3桁
    クロック目安＝1024Hz（1手約0.5秒）。
    """
    p = Asm()
    p.STI(0xC5, 0); p.STI(0xC6, 0); p.STI(0xC7, 1); p.MOVI(0, 0xB)   # リセット直後は 001B=27
    p.label('newn')                               # n = 入力の下3桁 + キー（R0）
    p.LD(4, 0xC5); p.LD(5, 0xC6); p.LD(6, 0xC7); p.MOV(7, 0)
    p.ST(0xC5, 5); p.ST(0xC6, 6); p.ST(0xC7, 7)
    p.STI(0xC0, 0); p.STI(0xC1, 0)
    p.label('loop')
    p.CALL('show'); p.JNZ('key')                  # 待ちの間にキー＝やり直し
    p.MOV(0, 7); p.SHR(0); p.JC('odd')
    # 偶数：÷2
    for lo, hi in ((7, 6), (6, 5), (5, 4)):
        p.SHR(lo); p.MOV(0, hi); p.SHR(0); p.JNC(f'h{lo}'); p.ADDI(lo, 7)
        p.label(f'h{lo}')
    p.SHR(4)
    p.JMP('count')
    p.label('odd')                                # 3n+1
    for k in range(4):
        p.MOV(k, 4 + k)
    for first in (True, False):
        (p.CLC if first else p.SEC)()
        for k in (3, 2, 1, 0):
            p.ADD(4 + k, k)
        p.JC('over')
    p.label('count')                              # 手数 +1（8bit）
    p.LD(0, 0xC0); p.CLC(); p.ADDI(0, 1); p.ST(0xC0, 0)
    p.LD(0, 0xC1); p.ADDI(0, 0); p.ST(0xC1, 0)
    p.MOVI(0, 1); p.XOR(0, 7)                     # n == 1 か
    p.OR(0, 4); p.OR(0, 5); p.OR(0, 6); p.JNZ('loop')
    p.CALL('show')
    p.OUTI(2, 0); p.OUTI(3, 0)                    # 手数を表示
    p.LD(0, 0xC1); p.OUT(0, 0); p.LD(0, 0xC0); p.OUT(1, 0)
    p.label('wait')
    p.IN(0, 1); p.JZ('wait')
    p.label('key')
    p.IN(0, 1); p.JNZ('key')                      # 離すのを待つ
    p.IN(0, 0); p.JMP('newn')
    p.label('over')                               # 16bit をあふれた
    for port in range(4):
        p.OUTI(port, 0xE)
    p.JMP('wait')

    p.label('show')                               # 4桁を出して約0.5秒待つ（キーで抜ける）
    p.OUT(2, 4); p.OUT(3, 5); p.OUT(0, 6); p.OUT(1, 7)
    p.MOVI(1, 2)
    p.label('d0')                                 # 内側は R0 の桁あふれまで（初期値は問わない）
    p.IN(2, 1); p.JNZ('dret'); p.ADDI(0, 1); p.JNC('d0')
    p.SUBI(1, 1); p.JNZ('d0')                     # 抜けたとき C=1 なので SEC 不要
    p.label('dret')
    p.RET()
    return p, 'コラッツ3n+1（16bit・キーを押すたびに右から1桁入れてやり直す／リセット直後は27）'


def ecosystem():
    """生態系ゲーム（ロトカ・ヴォルテラ型の個体数の振動に、キーで介入する）。

    草食 x・肉食 y（8bit・16進2桁。上段 OUT2 OUT3＝草食／下段 OUT0 OUT1＝肉食）。1世代:
      h  = x*y の上位バイト（＝x*y/256。y 回の足し算で求める）
      x' = min(255, x + x/8) − 2h      （0以下＝草食の絶滅）
      y' = min(255, y − y/8 + h)       （0＝肉食の絶滅）
    放っておくと周期47世代のサイクル（草 8〜86・肉 7〜49。肉が少し遅れて追いかける）。
    ÷8＝左へ1つずらして上位ニブル（はみ出した1ビットは ADDI x,0 で拾う）。
    キーパッド（世代の変わり目で読む＝表示が変わるまで押す）: 1＝草を植える(+16)
      2＝狩る(肉食−16。狩りすぎると絶滅) 0＝最初から（判定はコードの bit0→植える・bit1→狩る・
      どちらも0→最初から）。絶滅＝表示 0000・どれかのキーで最初から。
    植えて 255 を超えたら FF にして（表示を飛ばして）そのまま次の世代へ進む。
    1世代は y 回のループ＝肉食が多いほど遅い。クロック目安＝2048Hz（1世代 0.1〜0.6秒）。
    R1R2=x R3R4=y R5R6=h R7R0=作業 RAM 0xC0-C1＝y の退避
    """
    p = Asm()
    p.label('start')
    p.MOVI(1, 4); p.MOVI(2, 0); p.MOVI(3, 1); p.MOVI(4, 0)   # x=0x40 y=0x10
    p.label('loop')
    p.OUT(2, 1); p.OUT(3, 2); p.OUT(0, 3); p.OUT(1, 4)
    p.IN(7, 1); p.JZ('gen')                                 # DA
    p.label('kr')
    p.IN(0, 1); p.JNZ('kr')
    p.IN(7, 0)
    p.SHR(7); p.JC('plant'); p.SHR(7); p.JNC('start')       # bit1 でも bit0 でもなければ最初から
    p.SEC(); p.SUBI(3, 1); p.JNC('dead'); p.JMP('loop')     # 狩る：y −16
    p.label('plant')
    p.CLC(); p.ADDI(1, 1); p.JNC('loop')                    # 草を植える：x +16
    p.MOVI(1, 15); p.MOVI(2, 15)                            # あふれ＝FF でそのまま次の世代へ
    p.label('gen')
    p.ST(0xC0, 3); p.ST(0xC1, 4)
    p.MOVI(5, 0); p.MOVI(6, 0); p.MOVI(7, 0); p.MOVI(0, 0)
    p.label('pl')                                           # P(R5R6R7R0) = x*y
    p.SEC(); p.SUBI(4, 1); p.SUBI(3, 0); p.JNC('pd')
    p.CLC(); p.ADD(0, 2); p.ADD(7, 1); p.ADDI(6, 0); p.ADDI(5, 0)
    p.JMP('pl')
    p.label('pd')
    p.LD(3, 0xC0); p.LD(4, 0xC1)                            # h = R5R6
    # y' = y − y/8 + h
    p.MOV(7, 3); p.MOV(0, 4); p.CLC(); p.ADD(0, 0); p.ADD(7, 7)
    p.MOVI(0, 0); p.ADDI(0, 0)                              # y/8 = R0R7
    p.SEC(); p.SUB(4, 7); p.SUB(3, 0)
    p.CLC(); p.ADD(4, 6); p.ADD(3, 5); p.JNC('y1')
    p.MOVI(3, 15); p.MOVI(4, 15)
    p.label('y1')
    # x' = x + x/8 − 2h
    p.MOV(7, 1); p.MOV(0, 2); p.CLC(); p.ADD(0, 0); p.ADD(7, 7)
    p.MOVI(0, 0); p.ADDI(0, 0)                              # x/8 = R0R7
    p.CLC(); p.ADD(2, 7); p.ADD(1, 0); p.JNC('x1')
    p.MOVI(1, 15); p.MOVI(2, 15)
    p.label('x1')
    p.CLC(); p.ADD(6, 6); p.ADD(5, 5); p.JC('dead')         # 2h が 255 超＝確実に絶滅
    p.SEC(); p.SUB(2, 6); p.SUB(1, 5); p.JNC('dead')
    p.MOV(0, 1); p.OR(0, 2); p.JZ('dead')
    p.MOV(0, 3); p.OR(0, 4); p.JNZ('loop')
    p.label('dead')                                         # 絶滅＝0000：キーで最初から
    for port in range(4):
        p.OUTI(port, 0)
    p.label('dk')
    p.IN(0, 1); p.JZ('dk')
    p.label('dr')
    p.IN(0, 1); p.JNZ('dr'); p.JMP('start')
    return p, '生態系ゲーム（草食/肉食の振動・キー 1=草を植える 2=狩る 0=最初から）'


def melody():
    """音と光：きらきら星（著作権切れの旋律）。曲・音の長さ・テンポはすべてこの ROM が持つ。

    OUT0＝音程（0=休符 1〜15=ド〜2オクターブ上のド・ハ長調の白鍵）。Pico は OUT0 を読んで
    音（PWM）と色（NeoPixel）に変えるだけ（pico_codes/soundLight.py）。判断も記憶もしない。
    音の終わりに OUT0 を一瞬 0 にする＝同じ音が続いても Pico が鳴らし直せる。
    TB-04 が鳴らしている証拠＝クロックを変えるとテンポが変わる・マニュアルクロックで1音ずつ進む。
    曲＝A B B A の4フレーズ（A＝ドドソソララソ ファファミミレレド／B＝ソソファファミミレ）。
    クロック目安＝1024Hz（四分音符 約0.6秒）。RAM 0xC0＝待ちカウンタ
    """
    p = Asm()
    for port in (1, 2, 3):
        p.OUTI(port, 0)
    p.label('song')
    p.CALL('A'); p.CALL('B'); p.CALL('B'); p.CALL('A')
    p.CALL('beat2')                               # 1曲ごとに少し休む（OUT0=0 のまま）
    p.JMP('song')

    def phrase(notes):
        for n in notes:                           # 負の数＝2拍
            p.OUTI(0, abs(n)); p.CALL('beat2' if n < 0 else 'beat')
        p.RET()
    p.label('A')
    phrase((1, 1, 5, 5, 6, 6, -5, 4, 4, 3, 3, 2, 2, -1))
    p.label('B')
    phrase((5, 5, 4, 4, 3, 3, -2))

    p.label('beat2')                              # 2拍＝1拍ぶん伸ばしてから beat
    p.CALL('hold')
    p.label('beat')
    p.CALL('hold')
    p.OUTI(0, 0)                                  # 音の区切り（次の OUTI までの数命令だけ 0）
    p.RET()
    p.label('hold')                               # 約150命令
    p.STI(0xC0, 4)
    p.label('h1')
    p.MOVI(0, 0); p.CLC()
    p.label('h0')
    p.ADDI(0, 1); p.JNC('h0')
    p.LD(0, 0xC0); p.SEC(); p.SUBI(0, 1); p.ST(0xC0, 0); p.JNZ('h1')
    p.RET()
    return p, '音と光：きらきら星（OUT0=音程 1〜15・0=休符 → Pico が音と色に変える）'


# ---------------------------------------------------------------------
# 計算機2本の共通部品（キー＝MM74C922：コード→IN0・DA→IN1 bit0＝DEVLOG 08-16(2)）
# キーコード: 0-9=数字 A=＋ B=− C=× D=÷ E=＝/ENT F=C（コード＝値になるようにキーへ貼る）
# 数は 8bit（0〜255）を R1R2（上位・下位）に持つ。表示＝10進3桁（OUT3 OUT0 OUT1）、
# OUT2＝演算子（A/b/C/d）か E（255超・負・÷0・スタックの積みすぎ/空）。
# ---------------------------------------------------------------------
def _calc_main(p):
    """main: X を10進3桁で表示 → キーを1つ読む（R7=コード）→ R0=コード-10・C/Z を立てて抜ける。"""
    p.label('main')
    p.MOV(5, 1); p.MOV(6, 2)
    p.MOVI(3, 6); p.MOVI(4, 4); p.CALL('divr'); p.OUT(3, 0)      # 百
    p.MOVI(3, 0); p.MOVI(4, 10); p.CALL('divr'); p.OUT(0, 0); p.OUT(1, 6)
    p.label('key')
    p.IN(0, 1); p.JZ('key'); p.IN(7, 0)
    p.label('kr')
    p.IN(0, 1); p.JNZ('kr')                       # 離すのを待つ
    p.MOV(0, 7); p.SEC(); p.SUBI(0, 10)           # C=0 なら数字


def _calc_ops(p, div=True):
    """X(R1R2) = A(R3R4) op X。R0 = op コード（A=1010 B=1011 C=1100 D=1101）。"""
    p.SHR(0); p.JC('odd'); p.SHR(0); p.JC('add')
    p.MOVI(5, 0); p.MOVI(6, 0)                    # ×：A を X 回足す
    p.label('ml')
    p.SEC(); p.SUBI(2, 1); p.SUBI(1, 0); p.JNC('md')   # X-1（借り＝X は 0 だった）
    p.CLC(); p.ADD(6, 4); p.ADD(5, 3); p.JC('err'); p.JMP('ml')
    p.label('odd')
    p.SHR(0); p.JNC('div' if div else 'err')      # ÷ が無い版では D は E
    p.SEC(); p.SUB(4, 2); p.SUB(3, 1); p.JNC('err')   # −
    p.MOV(5, 3); p.MOV(6, 4)
    p.label('md')
    p.MOV(1, 5); p.MOV(2, 6); p.JMP('main')
    if div:
        p.label('div')
        p.MOV(0, 1); p.OR(0, 2); p.JZ('err')
        p.MOV(5, 3); p.MOV(6, 4); p.MOV(3, 1); p.MOV(4, 2); p.CALL('divr')
        p.MOV(1, 7); p.MOV(2, 0); p.JMP('main')
    p.label('add')                                # ＋（あふれたら err へ落ちる）
    p.CLC(); p.ADD(2, 4); p.ADD(1, 3); p.JNC('main')


def _calc_tail(p):
    p.label('err')
    p.OUTI(2, 0xE); p.JMP('zero')
    p.label('divr')                               # W(R5R6) ÷ N(R3R4) → 商 R7R0・余り W
    p.MOVI(7, 0); p.MOVI(0, 0)
    p.label('dl')
    p.SEC(); p.SUB(6, 4); p.SUB(5, 3); p.JNC('dd')
    p.ADDI(0, 0); p.ADDI(7, 0); p.JMP('dl')       # C=1 なので ADDI x,0 で +1
    p.label('dd')
    p.ADD(6, 4); p.ADD(5, 3); p.RET()             # 引きすぎを戻す


def calc_normal():
    """ふつうの計算機「数 演算子 数 ＝」。1キー1桁・四則・結果は 0〜255（10進3桁）。

    ＝のあと結果に続けて「演算子 数 ＝」とつなげられる。数字キーは X をその数字に置き換える。
    F(C)＝0 に戻す。E は 255超・負・÷0（商は切り捨て）。RAM 0xC0-C1＝A 0xC2＝演算子
    """
    p = Asm()
    p.STI(0xC0, 0); p.STI(0xC1, 0); p.STI(0xC2, 0xA)   # 演算子の前に＝でも X のまま
    p.label('clear')
    p.OUTI(2, 0)
    p.label('zero')
    p.MOVI(1, 0); p.MOVI(2, 0)
    _calc_main(p)
    p.JNC('digit')
    p.SUBI(0, 4); p.JZ('equal'); p.JC('clear')
    p.ST(0xC0, 1); p.ST(0xC1, 2); p.ST(0xC2, 7); p.OUT(2, 7)   # 演算子：A を取っておく
    p.JMP('zero')
    p.label('digit')
    p.MOVI(1, 0); p.MOV(2, 7); p.JMP('main')
    p.label('equal')
    p.OUTI(2, 0); p.LD(3, 0xC0); p.LD(4, 0xC1); p.LD(0, 0xC2)
    _calc_ops(p)
    _calc_tail(p)
    return p, 'ふつうの計算機（1キー1桁・四則・0〜255／キー: 0-9 A+ B− C× D÷ E= FC）'


def calc_rpn():
    """逆ポーランド記法の計算機。ハードウェアスタック（PUSH/POP）をそのまま演算スタックに使う。

    数字キー＝X を積んでから X をその数字に（1キー1桁。「3 4 ＋」で7）。E(ENT)＝X をもう1つ積む
    （「7 ENT ×」で49）。A＋ B− C×＝積んだ数を下ろして X と計算。F(C)＝X を0に。
    積めるのは3つまで（8段のうち2段×3＋表示の CALL 1段）。積みすぎ・空で演算は E。
    ÷ は96命令に入らないので無し（D を押すと E）。RAM 0xC3＝積んだ数
    """
    p = Asm()
    p.STI(0xC3, 0)
    p.label('clear')
    p.OUTI(2, 0)
    p.label('zero')
    p.MOVI(1, 0); p.MOVI(2, 0)
    _calc_main(p)
    p.JNC('digit')
    p.SUBI(0, 4); p.JZ('digit'); p.JC('clear')   # E(ENT)は数字と同じく積む
    p.OUT(2, 7)                                   # 演算：Y を下ろす（空なら E）
    p.LD(0, 0xC3); p.SEC(); p.SUBI(0, 1); p.JNC('err'); p.ST(0xC3, 0)
    p.POP(4); p.POP(3)
    p.MOV(0, 7)
    _calc_ops(p, div=False)
    _calc_tail(p)
    p.label('digit')                              # X を積む（3つまで）
    p.LD(0, 0xC3); p.SEC(); p.SUBI(0, 3); p.JZ('err'); p.ADDI(0, 4); p.ST(0xC3, 0)
    p.PUSH(1); p.PUSH(2)
    p.MOV(0, 7); p.SEC(); p.SUBI(0, 14); p.JZ('main')   # ENT は複製だけ
    p.MOVI(1, 0); p.MOV(2, 7); p.OUTI(2, 0); p.JMP('main')
    return p, '逆ポーランド計算機（スタックで演算・1キー1桁・＋−×・3段／E=ENT FC）'


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
    'hanoi': hanoi,
    'ishitori': ishitori,
    'kaprekar': kaprekar,
    'rule_ca': rule_ca,
    'collatz': collatz,
    'calc_normal': calc_normal,
    'calc_rpn': calc_rpn,
    'ecosystem': ecosystem,
    'melody': melody,
}
