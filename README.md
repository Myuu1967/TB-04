# TB-04

自作 4bit CPU **TB-04** のプロジェクトリポジトリです。
TD4 ライクなアーキテクチャをベースに、ALU とデコーダを ROM 実装した独自設計の 4bit CPU です。

回路図・PCB（KiCAD）から、アセンブラ・シミュレータ・テストプログラムまでを世代ごとにまとめています。

## バージョン構成

| 世代 | アドレス幅 | 状態 | ディレクトリ |
|---|---|---|---|
| **ver1** | 4bit（16命令） | 実機完成・全命令動作 | [`ver1/`](ver1/) |
| ver2 | 8bit（256語・データは4bitのまま） | 設計中 | [`ver2/`](ver2/) |
| ver3 | （12bit 化予定） | 構想中 | 追加予定 |

> ver2 以降は、本リポジトリの `ver1/` と並べて追加していきます。

## ver1 の中身

```
ver1/
  hardware/   KiCAD プロジェクト（回路図・PCB・カスタムシンボル/フットプリント）
  sim/        Python による CPU コアシミュレータ・アセンブラ・対話シミュレータ
  tools/      ROM データ生成ツール（ALU / デコーダ / プログラム）・アセンブラ・ロジアナ表示ツール
  codes/      サンプルプログラム・命令テスト（.ASM / .bin / .hex）
  pico_codes/ デバッグ用 簡易ロジックアナライザの Pico 側ファームウェア（MicroPython）
```

ハードウェアの詳細・KiCAD ライブラリの登録方法は [`ver1/hardware/README.md`](ver1/hardware/README.md) を参照してください。

### サンプルプログラム

実機で動かしたデモです。いずれも **16語ROM・4bit・16命令**という制約の中に収めています。

| プログラム | 内容 |
|---|---|
| [`LED_FLOW`](ver1/codes/LED_FLOW.ASM) | 流れるLED（シフト命令なしで実現） |
| [`counter`](ver1/codes/counter.asm) | カウントアップ／ダウン（IN で切替） |
| [`FIBONACCI`](ver1/codes/FIBONACCI.ASM) | フィボナッチ数列 mod 16（ピサノ周期 π(16)=24 で循環） |
| [`RAMEN_TIMER`](ver1/codes/RAMEN_TIMER.ASM) | ラーメンタイマー（TD4 オマージュ） |
| [`KAKEZAN_44`](ver1/codes/KAKEZAN_44.ASM) | かけ算 四四。4×4=16 が4bitで 0 になるのを停止条件に転用 |
| [`LIFE_CA`](ver1/codes/LIFE_CA.ASM) | 1次元セルオートマトン。あふれビットを帰還させ周期15で消えない |
| [`PRED_PREY`](ver1/codes/PRED_PREY.ASM) | 捕食者と被食者の個体数振動（周期6・足し算と引き算だけ） |
| [`MIXED_CORD`](ver1/codes/MIXED_CORD.ASM) | 上記7デモを1個の256語ROMに同梱。ROM上位ニブルの手動セレクタで切替 |

このほかに命令・ポートの動作確認用が17本あります。各プログラムの解説・出力列・アセンブル方法は [`ver1/codes/README.md`](ver1/codes/README.md) を参照してください。

## アーキテクチャ（ver1）

| 項目 | 仕様 |
|---|---|
| データ幅 | 4bit |
| アドレス幅 | 4bit |
| 汎用レジスタ | R0〜R3 |
| フラグ | C（キャリー）、Z（ゼロ） |
| 命令数 | 16命令（OPC 4bit） |
| ALU | ROM 実装（3bit opcode、8演算） |
| デコーダ | ROM 実装（28C256 × 2 並列） |
| プログラム ROM | 28C256 |
| 制御タイミング | 4フェーズ（WB → FCH → DCR → EXE、WB 始まり） |
| スタック | なし |

### 制御タイミングの要点

- 通常命令は開始から2クロック目でフェッチ、4クロック目で実行（全命令ディレイスロットなしの4クロック動作）
- ジャンプ命令のアドレス切り替えは EXE フェーズで実施（ディレイスロット回避）
- フラグは EXE で無条件ラッチ。`MOV`/`MOVI`/`OUT`/`OUTI` は C,Z を 0 クリアするため、**フラグを立てる演算命令の直後に分岐命令（JNC/JZ）を置く**運用とする

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

- 設計編 「【TB-04】4bitCPUの設計」: <https://tanuki-bayashin.hatenablog.com/entry/2026/05/27/140048>
- 完成編 「【TB-04】4bitCPUの完成（アドレス4bitバージョン）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/20/164917>
- ソースコード編 「【TB-04】4bitCPUのソースコード編（シリーズ完結）」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/25/220134>
- ロジックアナライザー編 「ラズベリーパイPicoによる簡易ロジックアナライザー」: <https://tanuki-bayashin.hatenablog.com/entry/2026/06/28/074330>
