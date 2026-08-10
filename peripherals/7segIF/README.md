# 7segIF — TB-04 用 4bit→7セグメント表示ユニット

本回路は ちぇりーたくあん氏 の nlp リポジトリ（<https://github.com/cherry-takuan/nlp> 、`nlp-16a/Hardware/debug`、CC BY-SA 4.0）を一部参考にし、改変して作成しています。本ユニットのハードウェアも CC BY-SA 4.0 で公開します。

自作 4bit CPU **TB-04** の OUT ポート（4bit）に外付けし、`0`〜`F` を1桁の7セグメントLEDに表示する周辺ユニットです。本体改造は不要で、OUT ポート端子に接続するだけで動作します。ver1／ver2 どちらとも組み合わせられる**版非依存**ユニットのため、リポジトリ直下の `peripherals/` に置いています。

## 構成

| 項目 | 内容 |
|---|---|
| MCU | CH32V003F4P6（WCH・RISC-V, TSSOP-20） |
| 表示器 | LTS-6960HR（コモンアノード・赤・1桁） |
| 電源 | 5V 単一（TB-04 の 74HC 系と共通） |
| デコード方式 | MCU のルックアップテーブル（`0`〜`F` → セグメントパターン） |
| コネクタ | J1（TB-04 OUT 入力）／J2（WCH-Link ＋ UART 兼用ヘッダ） |

## ディレクトリ

```
peripherals/7segIF/
  hardware/            回路図・基板（KiCAD, CC BY-SA 4.0）※完成時にコピー
  firmware/
    main.c             通常版（0〜F をリアルタイム表示）
    main_dp_blink.c    お遊び版（DP を 0.5 秒周期で点滅）
  LICENSE              CC BY-SA 4.0（ハードウェア設計に適用）
  README.md            このファイル
```

## 実配線

- 入力（TB-04 OUT → J1）: `D0=PC0  D1=PC1  D2=PC2  D3=PC3`（PORTC[3:0]）
- 出力（→ 7セグ, 各3.3K）: `a=PD0 b=PD1 c=PD2 d=PD3 e=PD4 f=PD5 g=PD6 DP=PD7`（PORTD[7:0]）
- コモンアノードのため、セグメントは MCU ピン LOW(0) で点灯。

## ファームのビルド・書き込み（MounRiver Studio ＋ WCH SPL）

1. CH32V003F4P6 の新規プロジェクトを作成し、生成される `User/main.c` を `firmware/main.c`（または `main_dp_blink.c`）の内容で**置き換える**。`main()` を持つファイルは1つだけにすること。
2. 初回書き込み時にコードプロテクトで弾かれる場合は、WCH-LinkUtility の `Target → Clear All Code Flash-Protect` で保護解除。接続リセットは **by power off**（本基板は NRST 線をヘッダに出していないため）。
3. **seg b（PD1）は既定で SDI（単線デバッグ）ピン**。ファーム側で SDI を無効化しないと seg b が点灯しません（本リポジトリのファームは対応済み：`GPIO_PinRemapConfig(GPIO_Remap_SDI_Disable, ENABLE)`）。SDI 無効化後はライブデバッグ不可、再書き込みは power-off unlock で行います。
4. **DP（PD7）は既定 NRST**。DP を光らせるにはオプションバイト `RST_MODE` を GPIO 側に設定します（数字 `a`〜`g` のみなら不要）。

## ライセンス

- **ハードウェア**（`hardware/`）: CC BY-SA 4.0。詳細・帰属は [`LICENSE`](./LICENSE) を参照。
- **ファームウェア**（`firmware/`）: ちぇりー氏の著作物に由来しない独自実装で、上記 CC BY-SA の対象外です。
