# TB-04 ver2 ブロック図（SVG）生成
import sys
W, H = 1820, 1015
out = []
def a(s): out.append(s)

FONT = "'Noto Sans JP','Yu Gothic','Meiryo',sans-serif"
INK, SUB, LINE = '#222', '#555', '#333'
BOARD = {'if': ('#e8f1fb', '#4a7fb5'), 'ctrl': ('#eaf6ea', '#4b8f4b'), 'alu': ('#fdf0e3', '#c07a2c')}

def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def text(x, y, t, size=12, weight='normal', fill=INK, anchor='start'):
    a(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(t)}</text>')

def board(key, x, y, w, h, title, sub):
    bg, fg = BOARD[key]
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{fg}" stroke-width="2"/>')
    text(x + 14, y + 26, title, 17, 'bold', fg)
    text(x + 14 + len(title) * 17 + 8, y + 26, sub, 12, 'normal', fg)

def block(key, x, y, w, h, title, ic, notes=()):
    fg = BOARD[key][1]
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fff" stroke="{fg}" stroke-width="1.6"/>')
    text(x + 10, y + 22, title, 15, 'bold')
    text(x + 10, y + 41, ic, 12, 'normal', fg)
    for i, n in enumerate(notes):
        text(x + 10, y + 59 + i * 16, n, 11, 'normal', SUB)

def wire(pts, arrow_end=True, arrow_start=False, width=1.6, color=LINE):
    d = ' '.join(f'{x},{y}' for x, y in pts)
    me = ' marker-end="url(#ar)"' if arrow_end else ''
    ms = ' marker-start="url(#as)"' if arrow_start else ''
    a(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}"{me}{ms}/>')

def hop(x, y):  # 交差点（バスの上を越える）: 白抜き
    a(f'<rect x="{x-5}" y="{y-6}" width="10" height="12" fill="#fff"/>')

def dot(x, y):
    a(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{LINE}"/>')

def label(x, y, t, anchor='start', size=11, weight='bold'):
    # 線の上に置く白地のラベル
    wpx = len(t) * size * 0.62 + 6
    rx = x - (wpx / 2 if anchor == 'middle' else (wpx if anchor == 'end' else 0))
    a(f'<rect x="{rx-1}" y="{y-size}" width="{wpx}" height="{size+4}" fill="#fff" opacity="0.9"/>')
    text(x + (3 if anchor == 'start' else (-3 if anchor == 'end' else 0)), y, t, size, weight, INK, anchor)

a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">')
a('<defs>'
  f'<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
  f'<marker id="as" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="{LINE}"/></marker>'
  '</defs>')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(20, 38, 'TB-04 ver2 ブロック図', 24, 'bold')
text(290, 38, 'データ 4bit × アドレス 8bit・1命令＝4クロック（FCH1 → FCH2 → DCR → EXE）', 13, 'normal', SUB)

# ---- 基板 ----
board('if', 20, 60, 330, 870, 'IF板', '')
board('ctrl', 370, 60, 940, 870, '制御板', '')
board('alu', 1330, 60, 470, 870, '演算板', '')
# ケーブル
for x, t in ((360, '40ピン'), (1320, '40ピン＋20ピン')):
    a(f'<rect x="{x-6}" y="66" width="12" height="40" fill="#999" rx="2"/>')
text(360, 122, '40ピン', 11, 'bold', SUB, 'middle')
text(1320, 122, '40＋20ピン', 11, 'bold', SUB, 'middle')
text(1320, 137, '20ピンは180°ひねる', 10, 'normal', SUB, 'middle')

R = {1: 150, 2: 290, 3: 430, 4: 570, 5: 710}   # 行の上端
BH = 90
C = {1: 395, 2: 700, 3: 1005}                 # 制御板の列
CW = 230

# ---- IF板 ----
block('if', 45, R[1], 270, BH, 'クロック・リセット', '74HC14 ＋ 外付け clock4096（74HC04・4040）',
      ['水晶（32.768kHz）は不使用', '→ CLK_CPU・~RST'])
block('if', 45, R[3], 270, BH, 'OUTポート ×4', '74HC377 ×4',
      ['MD をラッチして外部へ', '表示: OUT 4桁'])
block('if', 45, R[4], 270, BH, 'INポート ×4', '74HC244 ×4（DIPスイッチ／外部入力）',
      ['選ばれたポートが MD を駆動', '表示: IN 4桁'])

# ---- 制御板 ----
block('ctrl', C[1], R[1], CW, BH, '位相発生', '74HC161・74HC238', ['FCH1 / FCH2 / DCR / EXE'])
a(f'<rect x="{C[2]}" y="{R[1]}" width="{C[3]+CW-C[2]}" height="{BH}" rx="6" fill="none" stroke="#888" stroke-dasharray="5,4"/>')
text(C[2] + 12, R[1] + 24, '相信号（FCH1・FCH2・DCR・EXE）と CLK_CPU・~RST は全ブロックへ（線は省略）', 12, 'normal', SUB)
text(C[2] + 12, R[1] + 46, 'デコーダROMの制御信号（SEL_*・~WE・WR・PC_LOAD・SP_CU/CD・C_WE/Z_WE）も', 12, 'normal', SUB)
text(C[2] + 12, R[1] + 64, '各ブロックへ（線は省略）。条件分岐は C/Z をデコーダROMに入れて ROM の中で判定', 12, 'normal', SUB)

block('ctrl', C[1], R[2], CW, BH, '命令ROM', '28C256（ZIF・16バンク）', ['A0-7 → MD0-7', 'バンクはロータリースイッチ'])
block('ctrl', C[1], R[3], CW, BH, 'PC ＋ 分岐先MUX', '74HC161 ×2・74HC157 ×2',
      ['分岐先: OPR4-11 / MD（RET）', '表示: PC_Q 2桁'])
block('ctrl', C[1], R[4], CW, BH, 'アドレス源の選択', '74HC244 ×4・138・157・139',
      ['mAddr(OPR4-11)/PC_Q/SP/I-O', 'ポート番号 → IN/OUT選択'])
block('ctrl', C[1], R[5], CW, BH, 'SP（スタックポインタ）', '74HC193（3bit・リセットで7）',
      ['番地 0xF0 + SP', 'PUSH/CALL 後減・POP/RET 前増'])

block('ctrl', C[2], R[2], CW, BH, '命令レジスタ', '74HC273 ×2（byte1・byte2）',
      ['→ OPC0-3・OPR0-11', '表示: OPC・OPR 4桁'])
block('ctrl', C[2], R[4], CW, BH, '領域デコード・ゲート群', '74HC08・00・10・32・74AHC04',
      ['A3-7 → ROM / RAM の選択', '~OE・~CS・~WE を生成'])
block('ctrl', C[2], R[5], CW, BH, 'RAM ＋ スタック', '6116（2K×8）',
      ['RAM 0xC0-0xEF', 'スタック 0xF0-0xF7'])

block('ctrl', C[3], R[2], CW, BH, 'デコーダROM ＋ 制御ラッチ', '28C256 ×2・74HC273 ×2',
      ['OPC・OPR0-3・C/Z → 制御信号', 'DCR でラッチ'])
block('ctrl', C[3], R[3], CW, BH, 'Riアドレス選択', '74HC157',
      ['OPR8-10（通常）/ OPR0-2（LD・ST）', '→ sel_a0-2'])
block('ctrl', C[3], R[4], CW, BH, 'Yラッチ・Yドライバ', '74HC273・74HC244 ×2',
      ['DI → MD（ST・PUSH・OUT）', 'PC_Q → MD（CALL の戻り番地）'])

# ---- 演算板 ----
AX, AW = 1355, 420
block('alu', AX, R[1], AW, BH, 'デコーダROM（ALU用）＋ ラッチ', '28C256・74HC273',
      ['OPC・OPR0-3・C/Z → alu_code0-3（→ ALU ROM）', 'SEL_A・SEL_B・SEL_IMM（→ ALU入力MUX）／表示: alu_code 1桁'])
block('alu', AX, R[2], AW, BH, 'レジスタ R0-R7', '74HC161 ×8・書込先の選択 74HC138',
      ['sel_a0-2 で書き込むレジスタを選ぶ（EXE）', 'リセットで 0'])
block('alu', AX, R[3], AW, BH, '読出しMUX（aポート・bポート）', '74HC253 ×8',
      ['a = Ri、b = Rj を同時に読み出す'])
block('alu', AX, R[4], AW, BH, 'ALU入力MUX（a・b）', '74HC253 ×4',
      ['a: DOa / OPR（即値）', 'b: DOb / MD / OPR（即値）'])
block('alu', AX, R[5], 265, BH, 'ALU ROM', '28C256',
      ['alu_a・alu_b・alu_code・carry_in', '→ DI0-3・C・Z'])
block('alu', AX + 285, R[5], AW - 285, BH, 'フラグ C/Z', '74HC74',
      ['→ デコーダROM・', '  ALU ROM へ'])

# ---- バス ----
AY, MY = 840, 890
wire([(385, AY), (1300, AY)], arrow_end=False, width=5, color='#2d5d8a')
label(398, AY - 8, 'A0-7 アドレスバス', size=12)
wire([(30, MY), (1790, MY)], arrow_end=False, width=5, color='#8a2d2d')
label(398, MY + 24, 'MD0-7 メモリデータバス（表示: MD 2桁）', size=12)

# ---- 配線 ----
# クロック → 位相
wire([(315, R[1] + 45), (C[1], R[1] + 45)]); text(355, R[1] + 38, 'CLK_CPU', 10, 'bold', INK, 'middle'); text(355, R[1] + 62, '~RST', 10, 'bold', INK, 'middle')
# 命令ROM: A 入力, MD 出力（MD 縦線は命令レジスタへも分岐）
wire([(660, AY), (660, R[2] + 70), (C[1] + CW, R[2] + 70)]); dot(660, AY)
wire([(C[1] + CW, R[2] + 30), (680, R[2] + 30), (680, AY - 6)], arrow_end=False); hop(680, AY); wire([(680, AY + 6), (680, MY)])
dot(680, MY)
wire([(680, R[2] + 55), (C[2], R[2] + 55)]); dot(680, R[2] + 55)
# PC → アドレス源, SP → アドレス源
wire([(510, R[3] + BH), (510, R[4])]); label(516, R[4] - 12, 'PC_Q0-7', size=10)
wire([(510, R[5]), (510, R[4] + BH)]); label(516, R[5] - 10, 'SP0-2', size=10)
# アドレス源 → A バス
wire([(C[1] + CW, R[4] + 45), (640, R[4] + 45), (640, AY)]); dot(640, AY)
# アドレス源 → IN / OUT のストローブ
wire([(C[1], R[4] + 30), (355, R[4] + 30), (355, R[3] + 45), (315, R[3] + 45)]); label(318, R[3] + 38, 'OUTPUT0-3', size=10)
wire([(C[1], R[4] + 70), (315, R[4] + 70)]); label(318, R[4] + 63, 'INPUT0-3', size=10)
# IN → MD, MD → OUT
wire([(180, R[4] + BH), (180, MY)]); dot(180, MY)
wire([(32, MY), (32, R[3] + 30), (45, R[3] + 30)]); dot(32, MY)
# 命令レジスタ → デコーダ, → Riアドレス
wire([(C[2] + CW, R[2] + 25), (C[3], R[2] + 25)]); label(C[2] + CW + 4, R[2] + 18, 'OPC・OPR0-3', size=10)
wire([(C[2] + CW, R[2] + 70), (965, R[2] + 70), (965, R[3] + 45), (C[3], R[3] + 45)]); label(C[2] + CW - 2, R[2] + 104, 'OPR0-2・OPR8-10', size=10, anchor='end')
# 命令レジスタ → OPR4-11（PC・アドレス源・演算板へ）は注記
text(C[2] + 10, R[3] + 22, 'OPR4-11（byte2）は', 11, 'normal', SUB)
text(C[2] + 10, R[3] + 38, 'PC の分岐先・mAddr・', 11, 'normal', SUB)
text(C[2] + 10, R[3] + 54, '演算板の即値へ（線は省略）', 11, 'normal', SUB)
# 領域デコード ← A
wire([(950, AY), (950, R[4] + 45), (C[2] + CW, R[4] + 45)]); dot(950, AY)
# RAM ← A, RAM ↔ MD
wire([(760, AY), (760, R[5] + BH)]); dot(760, AY)
wire([(880, R[5] + BH), (880, AY - 6)], arrow_end=False, arrow_start=True); hop(880, AY)
wire([(880, AY + 6), (880, MY)], arrow_end=True); dot(880, MY)
# Yドライバ → MD
wire([(1120, R[4] + BH), (1120, AY - 6)], arrow_end=False); hop(1120, AY); wire([(1120, AY + 6), (1120, MY)]); dot(1120, MY)
# Riアドレス → レジスタ（sel_a）
wire([(C[3] + CW, R[3] + 45), (1300, R[3] + 45), (1300, R[2] + 25), (AX, R[2] + 25)]); label(1240, R[3] + 38, 'sel_a0-2', size=10)
# 演算板内の流れ
wire([(AX + 140, R[2] + BH), (AX + 140, R[3])]); label(AX + 146, R[3] - 14, 'R0-R7', size=10)
wire([(AX + 140, R[3] + BH), (AX + 140, R[4])]); label(AX + 146, R[4] - 14, 'DOa・DOb', size=10)
wire([(AX + 140, R[4] + BH), (AX + 140, R[5])]); label(AX + 146, R[5] - 14, 'alu_a・alu_b', size=10)
wire([(AX + 265, R[5] + 45), (AX + 285, R[5] + 45)])
# DI: ALU ROM → レジスタ（左の縦線）と → Yラッチ
wire([(AX, R[5] + 60), (1340, R[5] + 60), (1340, R[2] + 65), (AX, R[2] + 65)]); label(1336, R[3] + 80, 'DI0-3', size=10, anchor='end')
wire([(1340, R[4] + 30), (C[3] + CW, R[4] + 30)]); dot(1340, R[4] + 30); label(1240, R[4] + 23, 'DI0-3', size=10)
# MD → ALU入力MUX（b）
wire([(1790, MY), (1790, R[4] + 45), (AX + AW, R[4] + 45)]); dot(1790, MY)

# 凡例・注記
text(20, 960, '実機での変更（回路図には未反映）: クロックは外付け clock4096 から CLK_CPU へ（IF板の水晶発振は不使用）／'
     '制御板 U1509 の 9番ピンに RC 遅延（1kΩ＋220pF・~WE_RAM の誤書込対策）', 12, 'normal', SUB)
text(20, 980, '7セグ表示 17台: 制御板 8桁（OPC・OPR 4・MD 2・PC_Q 2）／演算板 1桁（alu_code）／IF板 8桁（OUT 4・IN 4）', 12, 'normal', SUB)
text(20, 1000, 'バスはどちらも三態で、A は mAddr・PC・SP・I/O、MD は命令ROM・RAM・INポート・Yドライバのうち1つだけが駆動する。線は主な流れだけを描き、各ブロックの入出力は枠内に書いた。', 12, 'normal', SUB)
a('</svg>')
open(sys.argv[1], 'w', encoding='utf-8').write('\n'.join(out))
