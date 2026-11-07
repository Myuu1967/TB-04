# TB-04 ver1（アドレス 4bit 版）

TB-04 の最初の世代です。データ 4bit・アドレス 4bit（16語）・16命令の構成で、2026年6月に実機で全命令の動作を確認しました。
リポジトリ全体の説明は [トップの README](../README.md) を参照してください。

## ディレクトリ

```
ver1/
  hardware/   KiCAD プロジェクト（回路図・PCB・カスタムシンボル/フットプリント）
  sim/        Python による CPU コアシミュレータ・アセンブラ・対話シミュレータ
  tools/      ROM データ生成ツール（ALU / デコーダ / プログラム）・アセンブラ・ロジアナ表示ツール
  codes/      サンプルプログラム・命令テスト（.ASM / .bin / .hex）
  pico_codes/ デバッグ用 簡易ロジックアナライザの Pico 側ファームウェア（MicroPython）
```

ハードウェアの詳細・KiCAD ライブラリの登録方法は [`hardware/README.md`](hardware/README.md) を参照してください。KiCAD は 9.0 で作成しています。

## アーキテクチャ

| 項目 | 仕様 |
|---|---|
| データ幅 | 4bit |
| アドレス幅 | 4bit |
| 汎用レジスタ | R0〜R3 |
| フラグ | C（キャリー）、Z（ゼロ） |
| 命令数 | 16命令（OPC 4bit） |
| ALU | ROM 実装（4bit コード・9演算） |
| デコーダ | ROM 実装（28C256 × 2 並列） |
| プログラム ROM | 28C256 |
| 制御タイミング | 4フェーズ（WB → FCH → DCR → EXE、WB 始まり） |
| スタック | なし |

### 制御タイミングの要点

- 通常命令は開始から2クロック目でフェッチ、4クロック目で実行（全命令ディレイスロットなしの4クロック動作）
- ジャンプ命令のアドレス切り替えは EXE フェーズで実施（ディレイスロット回避）
- フラグは EXE で無条件ラッチ。`MOV`/`MOVI`/`OUT`/`OUTI` は C,Z を 0 クリアするため、**フラグを立てる演算命令の直後に分岐命令（JNC/JZ）を置く**運用とする

## 命令セット

1命令＝1語（8bit）。上位ニブルがオペランド、下位ニブルが OPC です。
ビット配置の記号は `ii`=Ri、`jj`=Rj、`mmmm`=即値、`aaaa`=飛び先番地。

| OPC | 命令 | オペランド | ビット配置 | 動作 | ALU | C | Z |
|:-:|---|---|---|---|---|:-:|:-:|
| 0 | NOP | - | `0000 0000` | 何もしない（書き込みなし） | NOP | 0 | 0 |
| 1 | MOV | Ri,Rj | `iijj 0001` | Ri←Rj | PASS_A | 0 | 0 |
| 2 | MOVI | Im | `mmmm 0010` | R0←Im | PASS_A | 0 | 0 |
| 3 | OUT | Ri | `ii00 0011` | OUT←Ri | PASS_A | 0 | 0 |
| 4 | OUTI | Im | `mmmm 0100` | OUT←Im | PASS_A | 0 | 0 |
| 5 | IN | Ri | `ii00 0101` | Ri←IN | PASS_A_Z | 0 | ○ |
| 6 | JMP | Addr | `aaaa 0110` | PC←Addr | PASS_A | 0 | 0 |
| 7 | JNC | Addr | `aaaa 0111` | C==0でPC←Addr | PASS_A／NOP | 0 | 0 |
| 8 | JZ | Addr | `aaaa 1000` | Z==1でPC←Addr | PASS_A／NOP | 0 | 0 |
| 9 | AND | Ri,Rj | `iijj 1001` | Ri←Ri&Rj | AND | 0 | ○ |
| A | OR | Ri,Rj | `iijj 1010` | Ri←Ri\|Rj | OR | 0 | ○ |
| B | XOR | Ri,Rj | `iijj 1011` | Ri←Ri^Rj | XOR | 0 | ○ |
| C | ADD | Ri,Rj | `iijj 1100` | Ri←Ri+Rj | ADD | ○ | ○ |
| D | ADDI | Im | `mmmm 1101` | R0←R0+Im | ADD | ○ | ○ |
| E | SUB | Ri,Rj | `iijj 1110` | Ri←Ri−Rj | SUB | ○ | ○ |
| F | SUBI | Im | `mmmm 1111` | R0←R0−Im | SUBR | ○ | ○ |

- C・Z は EXE で毎命令ラッチします（`0`＝0 にクリア、`○`＝結果で決まる）。そのため、フラグを使う分岐はフラグを立てる演算の直後に置きます
- `MOVI`・`ADDI`・`SUBI` の対象は R0 固定です
- `JNC`・`JZ` は分岐するとき `PASS_A`、しないとき `NOP` として動きます

## ALU コード

ALU は ROM（入力 12bit＝a 4bit・b 4bit・コード 4bit）で、結果 y と C・Z を出します。

| コード | 名前 | y | C | Z |
|:-:|---|---|---|---|
| 0 | NOP | 0 | 0 | 0 |
| 1 | PASS_A | a | 0 | 0 |
| 2 | AND | a & b | 0 | y==0 |
| 3 | OR | a \| b | 0 | y==0 |
| 4 | XOR | a ^ b | 0 | y==0 |
| 5 | ADD | a + b | 桁上げ | y==0 |
| 6 | SUB | a − b | 0＝借り | y==0 |
| 7 | SUBR | b − a | 0＝借り | y==0 |
| 8 | PASS_A_Z | a（`IN` 用） | 0 | y==0 |
| 9〜15 | （予約） | 0 | 0 | — |

## サンプルプログラム

実機で動かしたデモです。いずれも **16語ROM・4bit・16命令**という制約の中に収めています。

| プログラム | 内容 |
|---|---|
| [`LED_FLOW`](codes/LED_FLOW.ASM) | 流れるLED（シフト命令なしで実現） |
| [`counter`](codes/counter.asm) | カウントアップ／ダウン（IN で切替） |
| [`FIBONACCI`](codes/FIBONACCI.ASM) | フィボナッチ数列 mod 16（ピサノ周期 π(16)=24 で循環） |
| [`RAMEN_TIMER`](codes/RAMEN_TIMER.ASM) | ラーメンタイマー（TD4 オマージュ） |
| [`KAKEZAN_44`](codes/KAKEZAN_44.ASM) | かけ算 四四。4×4=16 が4bitで 0 になるのを停止条件に転用 |
| [`LIFE_CA`](codes/LIFE_CA.ASM) | 1次元セルオートマトン。あふれビットを帰還させ周期15で消えない |
| [`PRED_PREY`](codes/PRED_PREY.ASM) | 捕食者と被食者の個体数振動（周期6・足し算と引き算だけ） |
| [`MIXED_CORD`](codes/MIXED_CORD.ASM) | 上記7デモを1個の256語ROMに同梱。ROM上位ニブルの手動セレクタで切替 |

このほかに命令・ポートの動作確認用が17本あります。各プログラムの解説・出力列・アセンブル方法は [`codes/README.md`](codes/README.md) を参照してください。

## シミュレータの起動

```
cd ver1/sim
python sim.py                        # デフォルト（counter）
python sim.py --prog counter         # 0〜F カウンタ
python sim.py --prog adder           # 加算デモ
python sim.py --prog counter --step  # 1ステップ実行
python sim.py --in 5                 # IN ポートを 5 に設定
```

## ROM データの生成

```
cd ver1/tools
python gen_alu_rom.py        # ALU ROM（alu_rom.bin / .hex）
python gen_decoder_rom.py    # デコーダ ROM（decoder_u22 / u23）
python gen_prog_rom.py       # プログラム ROM
```

## 関連記事

- 設計編「【TB-04】4bitCPUの設計」: <https://tanuki-bayashin.hatenablog.com/entry/2026/05/27/140048>
- 完成編「【TB-04】4bitCPUの完成（アドレス4bitバージョン）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/20/164917>
- ソースコード編「【TB-04】4bitCPUのソースコード編（シリーズ完結）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/25/220134>
- ロジックアナライザー編「ラズベリーパイPicoによる簡易ロジックアナライザー」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/28/074330>
