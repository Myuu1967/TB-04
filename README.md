# TB-04 (tanuki)

自作 4bit CPU **TB-04**（コード名: tanuki）のプロジェクトリポジトリです。
TD4 ライクなアーキテクチャをベースに、ALU とデコーダを ROM 実装した独自設計の 4bit CPU です。

回路図・PCB（KiCAD）から、アセンブラ・シミュレータ・テストプログラムまでを世代ごとにまとめています。

## バージョン構成

| 世代 | アドレス幅 | 状態 | ディレクトリ |
|---|---|---|---|
| **ver1** | 4bit（16命令） | 実機完成・全命令動作 | [`ver1/`](ver1/) |
| ver2 | （8bit 化予定） | 構想中 | 追加予定 |
| ver3 | （12bit 化予定） | 構想中 | 追加予定 |

> ver2 以降は、本リポジトリの `ver1/` と並べて追加していきます。

## ver1 の中身

```
ver1/
  hardware/   KiCAD プロジェクト（回路図・PCB・カスタムシンボル/フットプリント）
  sim/        Python による CPU コアシミュレータ・アセンブラ・対話シミュレータ
  tools/      ROM データ生成ツール（ALU / デコーダ / プログラム）・tanuki アセンブラ・ロジアナ表示ツール
  codes/      テストプログラム（.ASM / .bin / .hex）
  pico_codes/ デバッグ用 簡易ロジックアナライザの Pico 側ファームウェア（MicroPython）
  DEVLOG.md   開発ログ
```

ハードウェアの詳細・KiCAD ライブラリの登録方法は [`ver1/hardware/README.md`](ver1/hardware/README.md) を参照してください。

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
