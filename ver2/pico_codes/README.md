# pico_codes — Pico 高速ロジックアナライザ（ver2 用）

Raspberry Pi Pico の **PIO** で 125MHz（8ns 間隔）サンプリングし、トリガー直後の短い波形を取り込む自作ロジックアナライザです。
TB-04 ver2 のブリングアップで、CALL のスタック誤書込（RAM の書込パルスと PC の変化の競合、数十 ns）を測るために作りました。
ver1 の 10Hz 版（[`../../ver1/pico_codes/`](../../ver1/pico_codes/)）を元にしています。

| ファイル | 動く場所 | 役割 |
|---|---|---|
| `forLogiAna.py` | Pico（MicroPython） | トリガー待ち → 64 サンプル（512ns）取り込み → UART へ送信。これを繰り返す |
| `logicAnalyzer.py` | PC（Python 3・`pyserial`・`matplotlib`） | 指定回数受信して、全サンプルの表と判定を表示し、波形を `logicAnalyzer.png` に保存 |

## 配線（4ch）

入力は 5V 系なので分圧抵抗（1kΩ + 2kΩ）経由で Pico へ。UART0（GP0=TX / GP1=RX、115200bps）を USB シリアル変換で PC へつなぎます。

| Pico | ch | 信号 | 測定点（制御板） |
|---|---|---|---|
| GP2 | CH0 | `CLK_CPU` | `U501`-8 |
| GP3 | CH1 | `~WE_RAM` | `U1101`-21 |
| GP4 | CH2 | `~CS_RAM` | `U1101`-18 |
| GP5 | CH3 | `MD5` | `U1101`-15 |

## トリガー

**`~CS_RAM` = L のあいだに `CLK_CPU` が ↑**（RAM を読み書きする命令の EXE 末）。PIO の `wait` 3 命令で待ち、その後は 1 クロック 1 サンプルで取り込みます。RX FIFO（8 語）が満杯になると PIO が止まるので、最初の 8 語が連続した 64 サンプルになります。

## 使い方

1. Pico に MicroPython を書き込み、`forLogiAna.py` を実行（または `main.py` として配置）。UART に `READY,4,8,64` が出る
2. PC で `python logicAnalyzer.py COM13 2`（COM ポート・取り込む回数）
3. TB-04 をリセットして走らせる。テスト ROM バンク 12 なら取込 1＝最初の CALL、取込 2＝RET の EXE 末

コンソールには「**★ `~WE`・`~CS` 同時 L：何 ns〜何 ns、その間の MD5**」が出ます（書込が成立しうる窓）。

## 注意

- t=0 は `CLK↑` の約 20ns 後（PIO の入力同期と `wait` の遅れ）。パルスの始まりは欠けて見えることがある
- 分圧抵抗と配線容量で 10ns 程度なまる。パルス幅は目安
- チャンネルを 8 にするときは `NCH` と PIO 内の `in_(pins, 4)` の両方を 8 に（PIO 関数の中ではグローバル変数を参照できない）。8ch では 32 サンプル（256ns）になる
