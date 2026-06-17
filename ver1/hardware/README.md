# TB-04

自作4bitCPU **TB-04** のKiCADプロジェクトです。

## 概要

TD4ライクなアーキテクチャをベースに独自設計した4bitCPUです。
ALUとデコーダをROM実装し、汎用レジスタR0〜R3、フラグC/Zを持ちます。

## 現バージョン: 4bitアドレス版

| 項目 | 仕様 |
|------|------|
| データ幅 | 4bit |
| アドレス幅 | 4bit（16命令） |
| 汎用レジスタ | R0〜R3 |
| フラグ | C（キャリー）、Z（ゼロ） |
| ALU | ROM実装（8演算） |
| デコーダ | ROM実装（2個並列） |
| プログラムROM | 28C256（ZIFソケット） |
| 制御タイミング | 4フェーズ（FCH/DCR/EXE/WB） |

## 将来の拡張予定

- 8bitアドレス版
- 12bitアドレス版

## ライブラリの登録

このリポジトリにはカスタムシンボル・フットプリントが含まれています。
回路図・PCBを正しく開くには、KiCADのライブラリパスに以下を登録してください。

### シンボルライブラリ

`環境設定 → シンボルライブラリを管理` で以下を追加:

| ライブラリ名 | ファイル |
|---|---|
| `New_Library` | `symbols/New_Library.kicad_sym` |
| `originalCPU` | `symbols/originalCPU.kicad_sym` |
| `74HC161` | `symbols/74HC161N.kicad_sym` |

### フットプリントライブラリ

`環境設定 → フットプリントライブラリを管理` で以下を追加:

| ライブラリ名 | フォルダ |
|---|---|
| `Library` | `footprints/Library.pretty` |

## KiCADプロジェクト構成

| シート | 内容 |
|--------|------|
| TB04addr4bitVer3.kicad_sch | トップシート（電源・WEデコード） |
| RS.kicad_sch | レジスタR0〜R3（74HC161 × 4 + 74HC253 × 3） |
| RS01.kicad_sch | 追加レジスタ・プログラム入力 |
| ROM_ALU_Decoder.kicad_sch | 28C256 × 4 + PC + フラグ |
| ALU.kicad_sch | LEDモニターインターフェース |
| clk_rst.kicad_sch | クロック・リセット |
| TB04addr4bitVer3.kicad_pcb | PCBレイアウト |
