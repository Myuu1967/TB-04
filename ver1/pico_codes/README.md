# pico_codes — Pico 簡易ロジックアナライザ（送信側）

デバッグに使用した自作ロジックアナライザの **Raspberry Pi Pico 側ファームウェア**（MicroPython）です。
PC 側の表示ツールは [`../tools/logic_monitor.py`](../tools/logic_monitor.py) を使います。

## forLogiAna.py

- Pico の **GP2〜GP8 を 7ch（CH0〜CH6）の入力**として読み取り、`UART0`（GP0=TX / GP1=RX、115200bps）で CSV 形式に送信します
- フォーマット: `経過秒,CH0,CH1,...,CH6`（10Hz サンプリング）
- 入力は分圧抵抗（例: 1kΩ + 2kΩ）経由で接続

## 使い方

1. Pico に MicroPython を書き込み、`forLogiAna.py` を `main.py` として配置（または実行）
2. Pico の GP0/GP1 を USB シリアル変換に接続し、PC 側で COM ポートを確認
3. PC 側で `python ../tools/logic_monitor.py`（COM ポートはスクリプト内の設定に合わせる）

> ロジックアナライザの製作経緯・回路の詳細は別記事で解説予定です。
