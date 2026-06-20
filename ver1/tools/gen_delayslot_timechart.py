# -*- coding: utf-8 -*-
"""
TB-04 ver.1 ブログ完成編 4.3節用
ジャンプのディレイスロット解消 before/after タイムチャート（模式図）
Before: PC書込(ジャンプ先)が WB で遅く、次フェッチが PC+1 を取り込み
        → ディレイスロットの命令が実行されてしまう
After : PC書込を DEC へ前倒し（CNTABL=DEC·NOT_JMP, 書込はEXE）
        → 次フェッチがジャンプ先になり、余分な命令はスキップ
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

for _f in ["Meiryo", "Yu Gothic", "MS Gothic", "Noto Sans CJK JP", "MS PGothic"]:
    try:
        font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

NCYC = 3           # 命令サイクル数
NCLK = NCYC * 4    # クロック数
PHASES = ["FCH", "DEC", "EXE", "WB"]
PH_COLOR = {"FCH": "#f6b4b4", "DEC": "#a9cdf2", "EXE": "#a6e3bf", "WB": "#f3dd9a"}
PH_EDGE = {"FCH": "#d33", "DEC": "#1769c7", "EXE": "#1a9c4e", "WB": "#c79a16"}

PH_Y0, PH_H = 3.0, 0.7
IN_Y0, IN_H = 1.45, 0.9


def draw_panel(ax, inst_boxes, load_clk, load_label, pc_values,
               title, note, note_color, extra_note=None):
    # サイクル境界の薄い縦線
    for c in range(NCYC + 1):
        ax.axvline(c * 4, color="0.75", lw=0.9, ls="--", zorder=0)

    # フェーズ列（クロック単位）
    ax.text(-0.2, PH_Y0 + PH_H / 2, "フェーズ", ha="right", va="center",
            fontsize=10.5, fontweight="bold")
    for k in range(NCLK):
        ph = PHASES[k % 4]
        ax.add_patch(Rectangle((k, PH_Y0), 1, PH_H, fc=PH_COLOR[ph],
                               ec=PH_EDGE[ph], lw=1.0, zorder=2))
        ax.text(k + 0.5, PH_Y0 + PH_H / 2, ph, ha="center", va="center",
                fontsize=7.5, color="#333", zorder=3)

    # PC書込タイミングの矢印＋ラベル
    lx = load_clk + 0.5
    ax.annotate("", xy=(lx, PH_Y0 - 0.02), xytext=(lx, PH_Y0 + PH_H + 0.32),
                arrowprops=dict(arrowstyle="->", color=note_color, lw=2.0), zorder=4)
    ax.text(lx, PH_Y0 + PH_H + 0.40, load_label, ha="center", va="bottom",
            fontsize=9, color=note_color, fontweight="bold")

    # 命令サイクル（フェッチ＆実行）
    ax.text(-0.2, IN_Y0 + IN_H / 2, "フェッチ\n＆実行", ha="right", va="center",
            fontsize=10.5, fontweight="bold")
    for b in inst_boxes:
        ax.add_patch(Rectangle((b["x0"], IN_Y0), 4, IN_H, fc=b["fc"],
                               ec=b["ec"], lw=1.6, zorder=2))
        ax.text(b["x0"] + 2, IN_Y0 + IN_H / 2, b["label"], ha="center",
                va="center", fontsize=9.5, color="#222", zorder=3)

    # PC値
    ax.text(-0.2, 0.75, "PC値", ha="right", va="center",
            fontsize=10.5, fontweight="bold")
    for c, pv in enumerate(pc_values):
        ax.text(c * 4 + 2, 0.75, pv, ha="center", va="center", fontsize=10,
                color="#444", fontweight="bold")

    # パネル見出し
    ax.text(-1.0, 4.95, title, ha="left", va="center", fontsize=12,
            fontweight="bold", color=note_color)
    # 右の注釈
    ax.text(NCLK + 0.3, IN_Y0 + IN_H / 2 + 0.4, note, ha="left", va="center",
            fontsize=9.5, color="#333",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=note_color, lw=1.3))
    if extra_note:
        ax.text(NCLK + 0.3, 0.75, extra_note, ha="left", va="center",
                fontsize=9, color="#777")

    ax.set_xlim(-1.7, NCLK + 4.6)
    ax.set_ylim(-0.2, 5.3)
    ax.axis("off")


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 7.2))

# Before：ディレイスロットあり
draw_panel(
    ax1,
    inst_boxes=[
        {"x0": 0, "label": "@1  JMP 5", "fc": "#eef1f5", "ec": "#888"},
        {"x0": 4, "label": "@2  命令A（ディレイスロット）", "fc": "#fde3e3", "ec": "#d33"},
        {"x0": 8, "label": "@5  命令T（ジャンプ先）", "fc": "#d7f0df", "ec": "#1a9c4e"},
    ],
    load_clk=3,  # WB of cyc1
    load_label="PC←5 を WB で書込（遅い）",
    pc_values=["PC=1", "PC=2", "PC=5"],
    title="Before：PC書込がWB（ディレイスロットあり）",
    note="書込が遅く、次フェッチは PC+1=2 を\n取り込む → @2 命令A が実行されてしまう\n（ジャンプ先は1サイクル遅れて @5 へ）",
    note_color="#d33",
)

# After：ディレイスロットなし
draw_panel(
    ax2,
    inst_boxes=[
        {"x0": 0, "label": "@1  JMP 5", "fc": "#eef1f5", "ec": "#888"},
        {"x0": 4, "label": "@5  命令T（ジャンプ先）", "fc": "#d7f0df", "ec": "#1a9c4e"},
        {"x0": 8, "label": "@6  次命令", "fc": "#eef1f5", "ec": "#888"},
    ],
    load_clk=1,  # DEC of cyc1
    load_label="PC←5 を DEC で書込（早い）",
    pc_values=["PC=1", "PC=5", "PC=6"],
    title="After：PC書込をDECへ前倒し（ディレイスロットなし）",
    note="書込が早く、次フェッチがジャンプ先 @5 に\nなる → 4クロックでジャンプ完了\n（CNTABL=DEC·NOT_JMP／書込はEXE）",
    note_color="#1a9c4e",
    extra_note="※ @2 命令A はスキップ（実行されない）",
)

fig.suptitle("ジャンプのディレイスロット解消（PC書込タイミング WB→DEC）",
             fontsize=13.5, fontweight="bold", y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.96])
out = "delayslot_timechart.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print("saved:", out)
