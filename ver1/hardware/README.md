# TB-04 ver1 ハードウェア

自作4bitCPU **TB-04** の ver1（アドレス4bit版・2026-06 完成）の KiCAD プロジェクトです。
仕様・命令セット・使い方は [`ver1/README.md`](../README.md) を参照してください。

| 項目 | 仕様 |
|------|------|
| データ幅 | 4bit |
| アドレス幅 | 4bit（16語） |
| 汎用レジスタ | R0〜R3 |
| フラグ | C（キャリー）、Z（ゼロ） |
| ALU | ROM実装（4bitコード・9演算） |
| デコーダ | ROM実装（28C256 × 2 並列） |
| プログラムROM | 28C256（ZIFソケット） |
| 制御タイミング | 4フェーズ（WB → FCH → DCR → EXE、WB 始まり）・1命令＝4クロック |

回路図の PDF: [`4bit-addr/TB04addr4bitVer3.pdf`](4bit-addr/TB04addr4bitVer3.pdf)

## 回路図・PCB と実機の関係

- 実機は、最初に製作した PCB に**立体配線で改造**を加えたものです（2026-06-15、ジャンプのディレイスロットをなくすためにフェーズ構成を変更）。
- **回路図はこの改造を反映済み**です（2026-06-30・08-10 に修正）。
- **PCB ファイル（`TB04addr4bitVer3.kicad_pcb`）は改造の反映が途中**で、未配線や短絡が残っています。このままでは製造に使えません。

アドレスを 8bit に広げた後継は [`ver2/`](../../ver2/) です。

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
| RS.kicad_sch | レジスタ群①：汎用レジスタ R0〜R3（74HC161・74HC253） |
| RS01.kicad_sch | レジスタ群②：PC・入出力ポート・OPR から ALU への出力（即値） |
| ROM_ALU_Decoder.kicad_sch | 28C256 × 4 + PC + フラグ |
| ALU.kicad_sch | LEDモニターインターフェース |
| clk_rst.kicad_sch | クロック・リセット |
| TB04addr4bitVer3.kicad_pcb | PCBレイアウト |
