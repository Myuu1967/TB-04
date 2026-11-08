# TB-04 ver2（アドレス 8bit 版）

TB-04 の2世代目です。データは 4bit のまま、アドレスを 8bit（256語）に広げ、RAM とスタックを加えました。
12bit アドレスの ver3 へ向けた通過点として作り、2026年10月にテストプログラムで全命令の動作を確認しました。
リポジトリ全体の説明は [トップの README](../README.md) を参照してください。

## アーキテクチャ

| 項目 | 仕様 |
|---|---|
| データ幅 | 4bit |
| アドレス幅 | 8bit（256語） |
| 命令形式 | 固定2語（2バイト）。1語目の上位ニブルが opcode、`E`/`F` は 8bit opcode へのプレフィックス |
| 命令数 | 34命令（ロード/ストア・PUSH/POP・CALL/RET・条件分岐4種・シフト/ローテートなど） |
| 汎用レジスタ | R0〜R7 |
| フラグ | C（キャリー）、Z（ゼロ）。書き込む命令だけが更新する（クロックゲート方式） |
| ALU | ROM 実装（28C256・入力 13bit・16演算） |
| デコーダ | ROM 実装（28C256 × 3） |
| プログラム ROM | 28C256（ZIF ソケット） |
| RAM・スタック | 6116 1個を共用。スタックは8段（SP は 3bit） |
| 制御タイミング | 4フェーズ（FCH1 → FCH2 → DCR → EXE）、1命令＝4クロック |
| 表示 | 7セグメント表示ユニット [7segIF](../peripherals/7segIF/) を17台直挿し（命令・MD・PC・OUT・IN など）＋ LED |

### メモリマップ

| アドレス | 用途 |
|---|---|
| `0x00`〜`0xBF` | プログラム ROM（192語＝96命令） |
| `0xC0`〜`0xEF` | RAM（データ 4bit） |
| `0xF0`〜`0xF7` | スタック（戻り番地 8bit） |
| `0xF8`〜`0xFB` | IN ポート 0〜3 |
| `0xFC`〜`0xFF` | OUT ポート 0〜3 |

## 命令セット

1命令＝2語（byte1・byte2）。byte1 の上位ニブルが opcode で、`1110`（E系）・`1111`（F系）のときは下位ニブルまで含めた 8bit が opcode になります。
ビット配置の記号は `iii`=Ri、`jjj`=Rj、`mmmm`=即値、`aaaa aaaa`=番地、`pp`=ポート番号。

| 群 | 命令 | オペランド | byte1 | byte2 | 動作 | Z | C | ALU |
|---|---|---|---|---|---|:-:|:-:|---|
| 単独ニブル | NOP | - | `0000 0000` | `0000 0000` | 何もしない | - | - | NOP |
| 単独ニブル | MOV | Ri,Rj | `0001 0000` | `0iii 0jjj` | Ri←Rj | - | - | PASS_B |
| 単独ニブル | MOVI | Ri,Im4 | `0010 mmmm` | `0iii 0000` | Ri←Im4 | - | - | PASS_A |
| 単独ニブル | LD | Ri,[Im8] | `0011 0iii` | `aaaa aaaa` | Ri←MEM[Im8] | - | - | PASS_B |
| 単独ニブル | ST | [Im8],Ri | `0100 0iii` | `aaaa aaaa` | MEM[Im8]←Ri | - | - | PASS_A |
| 単独ニブル | STI | [Im8],Im4 | `0101 mmmm` | `aaaa aaaa` | MEM[Im8]←Im4 | - | - | PASS_A |
| 単独ニブル | （予約） | - | `0110/0111/1000` | — | ver3（12bitアドレス化）拡張用に温存（3枠） | - | - | - |
| E系 | JMP | Addr | `1110 0000` | `aaaa aaaa` | PC←Addr | - | - | - |
| E系 | JC | Addr | `1110 0001` | `aaaa aaaa` | C==1でPC←Addr | - | - | - |
| E系 | JNC | Addr | `1110 0010` | `aaaa aaaa` | C==0でPC←Addr | - | - | - |
| E系 | JZ | Addr | `1110 0011` | `aaaa aaaa` | Z==1でPC←Addr | - | - | - |
| E系 | JNZ | Addr | `1110 0100` | `aaaa aaaa` | Z==0でPC←Addr | - | - | - |
| E系 | CALL | Addr | `1110 0101` | `aaaa aaaa` | MEM[SP]←PC; PC←Addr; SP-- | - | - | - |
| E系 | RET | - | `1110 0110` | `0000 0000` | SP++; PC←MEM[SP] | - | - | - |
| 擬似 | HALT | - | — | — | PC←自番地（JMP $ に展開）。opcode 1110 0111 は予約 | - | - | - |
| E系 | PUSH | Ri | `1110 1000` | `0iii 0000` | MEM[SP]←Ri; SP-- | - | - | PASS_A |
| E系 | POP | Ri | `1110 1001` | `0iii 0000` | SP++; Ri←MEM[SP] | - | - | PASS_B |
| E系 | IN | Ri,port | `1110 1010` | `0iii 00pp` | Ri←IN[port] | ○ | - | PASS_B |
| E系 | OUT | port,Ri | `1110 1011` | `0iii 00pp` | OUT[port]←Ri | - | - | PASS_A |
| E系 | OUTI | port,Im4 | `1110 1100` | `00pp mmmm` | OUT[port]←Im4 | - | - | PASS_A |
| F系 | CP | Ri,Rj | `1111 0000` | `0iii 0jjj` | Ri−Rj（フラグのみ） | ○ | ○ | SUB |
| F系 | AND | Ri,Rj | `1111 0001` | `0iii 0jjj` | Ri←Ri&Rj | ○ | - | AND |
| F系 | OR | Ri,Rj | `1111 0010` | `0iii 0jjj` | Ri←Ri\|Rj | ○ | - | OR |
| F系 | XOR | Ri,Rj | `1111 0011` | `0iii 0jjj` | Ri←Ri^Rj | ○ | - | XOR |
| F系 | NOT | Ri | `1111 0100` | `0iii 0000` | Ri←!Ri | ○ | - | NOT |
| F系 | SHL | Ri | `1111 0101` | `0iii 0000` | [C,Ri]←[Ri,0] | ○ | ○ | SHL |
| F系 | SHR | Ri | `1111 0110` | `0iii 0000` | [Ri,C]←[0,Ri] | ○ | ○ | SHR |
| F系 | ROL | Ri | `1111 0111` | `0iii 0000` | Ri←{Ri[2:0],Ri[3]} | - | - | ROL |
| F系 | ROR | Ri | `1111 1000` | `0iii 0000` | Ri←{Ri[0],Ri[3:1]} | - | - | ROR |
| F系 | ADD | Ri,Rj | `1111 1001` | `0iii 0jjj` | [C,Ri]←Ri+Rj+Cin | ○ | ○ | ADD |
| F系 | ADDI | Ri,Im | `1111 1010` | `0iii mmmm` | [C,Ri]←Ri+Im+Cin | ○ | ○ | ADD |
| F系 | SUB | Ri,Rj | `1111 1011` | `0iii 0jjj` | [C,Ri]←Ri−Rj−1+Cin | ○ | ○ | SUB |
| F系 | SUBI | Ri,Im | `1111 1100` | `0iii mmmm` | [C,Ri]←Ri−Im−1+Cin | ○ | ○ | SUB |
| F系 | CLC | - | `1111 1101` | `0000 0000` | C←0 | - | ○ | CLC(14) |
| F系 | SEC | - | `1111 1110` | `0000 0000` | C←1 | - | ○ | SEC(15) |
| F系 | （予約） | - | `1111 1111` | — | 将来用に予約 | - | - | - |

- Z・C の `○` はその命令でフラグを更新、`-` は保持します。`Cin` は現在の C です（`ADD`・`SUB` の前に `CLC`／`SEC` で整えます）
- `LD`・`ST` だけは Ri を byte1 に持ちます
- 先頭ニブルが `6`〜`D` の未定義命令は NOP として動きます

## ALU コード

ALU は ROM（入力 13bit＝a 4bit・b 4bit・コード 4bit・Cin）で、結果 y と Cout・Z（＝y==0）を出します。
フラグに採用するかどうかは、命令ごとにデコーダが決めます（上の表の Z・C 列）。

| コード | 名前 | y | Cout |
|:-:|---|---|---|
| 0 | NOP | 0 | 0 |
| 1 | PASS_A | a | 0 |
| 2 | PASS_B | b | 0 |
| 3 | AND | a & b | 0 |
| 4 | OR | a \| b | 0 |
| 5 | XOR | a ^ b | 0 |
| 6 | NOT | ~a | 0 |
| 7 | SHL | {a[2:0], 0} | a[3] |
| 8 | SHR | {0, a[3:1]} | a[0] |
| 9 | ROL | {a[2:0], a[3]} | 0 |
| 10 | ROR | {a[0], a[3:1]} | 0 |
| 11 | ADD | a + b + Cin | 桁上げ |
| 12 | SUB | a − b − 1 + Cin | 0＝借り |
| 13 | （予約） | 0 | 0 |
| 14 | CLC | 0 | 0 |
| 15 | SEC | 0 | 1 |

## ディレクトリ

```
ver2/
  hardware/
    基板分割_0827/    実際に製作した3枚の基板（回路図・PCB）
      TB04addr8bit_if/     IF 板（クロック・リセット・入出力）
      TB04addr8bit_ctrl/   制御板
      TB04addr8bit_alu/    演算板
    footprints/       カスタムフットプリント
  sim/                Python による CPU モデル・アセンブラ・デモプログラム・テスト
  tools/              ROM データ生成ツール（ALU / デコーダ / ブリングアップ用テスト ROM）と生成済み ROM
  ver2_decoder_truthtable.csv   デコーダ ROM の真理値表（gen_decoder_rom.py の入力）
  pico_codes/         Pico PIO 高速ロジックアナライザ（8ns 分解能）
```

KiCAD は 10.0 で作成しています（9.0 では開けません）。

`hardware/TB04addr8bit_copy/` は、3枚に分割する前の1枚の回路図です（分割作業の元にした版で、その後の基板側の修正は反映していません）。

3枚の基板はケーブル（40ピン＋40ピン＋20ピン）で IF 板－制御板－演算板の順につなぎます。**20ピンのケーブルは 180°ひねって挿します。**

## 回路図と実機の違い

公開している回路図・PCB に対して、実機では次の2点を変えています（回路図には反映していません）。

- **クロック**：IF 板の水晶発振（32.768kHz＋74HC4060）は、周波数が安定しなかったため使っていません。代わりに外付けのクロック供給ユニット [`clock4096`](../peripherals/clock4096/) からクロックを入れています。IF 板の手動クロックの信号をユニットへ回し、ユニットのスライドスイッチで切り替えた出力を IF 板の `CLK_CPU` につないでいます。
- **RAM の書込パルス**：CALL でスタックに誤って書き込む不具合の対策として、制御板の `U1509` の 9 番ピンを浮かせ、パッドとの間に 1kΩ を直列に入れ、9 番ピンと GND の間に 220pF をつないでいます（クロックを約 150ns 遅らせる）。経緯は完成編の記事を参照してください。

## シミュレータと ROM 生成ツール

Python 3 の標準ライブラリだけで動きます。

```
cd ver2/sim
python test_cpu.py                     # 全命令のテスト
python sim.py --prog counter --trace   # 1命令ごとに PC・SP・R0〜R3・C/Z・OUT を表示
python cpu_phase.py --prog countdown   # 4フェーズ（FCH1/FCH2/DCR/EXE）単位で実行
```

デモ（`--prog`）は `counter`・`led_flow`・`fibonacci`・`ramen_timer`・`kakezan`・`life_ca`・`pred_prey`・`calc`・`sec_count`・`showcase`（展示デモ）です。プログラムは `programs.py` に Python のコードで書いています。

`cpu.py`（命令単位）は、命令の実行結果（レジスタ・フラグ・RAM・OUT）が実機と一致します（テスト ROM の期待値をこのモデルで求め、実機は全バンク合格）。実機との違いは次のとおりです。

- リセット直後の C/Z・OUT・RAM を 0 にしています（実機では不定）。
- `cpu_phase.py` は POP/RET の SP 更新などを EXE にまとめており、フェーズ単位では実機と異なるところがあります。
- ns 単位のタイミング（ゲート遅延やヒゲ）は扱いません。

```
cd ver2/tools
python gen_alu_rom.py       # alu_rom.bin / .hex（ALU ROM U603）
python gen_decoder_rom.py   # decoder_romA/B/C.bin / .hex（デコーダ ROM U704/U703/U706）
python gen_test_rom.py      # test_rom.bin / .hex（命令 ROM U604 用・16バンク）
```

テスト ROM は 1バンク＝256バイトで、制御板のロータリースイッチ `SW601` の位置がバンク番号になります。バンク 0〜14 は命令を依存順に1グループずつ確かめるテスト、バンク 15 は展示デモ（`showcase`）です。

## 高速ロジックアナライザ

ブリングアップで見つかった CALL のスタック誤書込（RAM の書込パルスと PC の変化の競合、数十 ns）を測るために作りました。使い方は [`pico_codes/README.md`](pico_codes/README.md) を参照してください。

## 関連記事

- 設計編「【TB-04】4bitCPUの設計（addr 8bit ver）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/11/03/164404>
- 回路図とPCB設計編「【TB-04】4bitCPUの回路図とPCB設計(addr 8bit ver)」: <https://tanuki-bayashin.hatenablog.com/entry/2026/11/05/082909>
- 完成編「【TB-04】4bitCPUの完成（addr 8bit ver）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/11/07/110004>
- デモ動画: <https://www.youtube.com/watch?v=xa86bRDYqcg>
