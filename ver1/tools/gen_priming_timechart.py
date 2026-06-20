# -*- coding: utf-8 -*-
"""
TB-04 ver.1 ブログ完成編 4.3節用
リセット起動時のフェーズ・プライミング before/after タイムチャート（模式図）
Before: リセット後 FCH 始まり → 1命令めがラッチされず1命令遅れ
After : リセット後 WB(空打ち) 始まり → 続くFCHで正しくラッチ、1命令めから実行
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

N = 8  # 表示クロック数
PH_COLOR = {"FCH": "#f6b4b4", "DEC": "#a9cdf2", "EXE": "#a6e3bf", "WB": "#f3dd9a"}
PH_EDGE = {"FCH": "#d33", "DEC": "#1769c7", "EXE": "#1a9c4e", "WB": "#c79a16"}

# 各行のy（パネル内ローカル）
Y_RST, Y_CLK = 3.55, 2.6
PH_Y0, PH_H = 1.3, 0.75
VL_Y0, VL_H = 0.2, 0.75
AMP = 0.7


def draw_panel(ax, phase_seq, valid_from, title, note, note_color, wb_prime_k=None):
    # フェーズ縦帯＋点線
    for k in range(N):
        ax.axvline(k, color="0.8", lw=0.7, ls="--", zorder=0)
    ax.axvline(N, color="0.8", lw=0.7, ls="--", zorder=0)

    # /RESET（負論理: 0=アサート, x>=0で解除）
    ax.step([-1, 0, N], [Y_RST, Y_RST + AMP, Y_RST + AMP], where="post",
            color="#222", lw=1.7, zorder=3)
    ax.text(-0.15, Y_RST + AMP / 2, "/RESET", ha="right", va="center",
            fontsize=11, fontweight="bold")
    ax.annotate("リセット解除", xy=(0, Y_RST + AMP), xytext=(0.6, Y_RST + AMP - 0.32),
                fontsize=8, color="#555",
                arrowprops=dict(arrowstyle="->", color="#999", lw=1.0))

    # clk_cpu
    cx, cy = [-1], [Y_CLK]
    for k in range(-1, N):
        cx += [k, k + 0.5]
        cy += [Y_CLK + AMP, Y_CLK]
    ax.step(cx, cy, where="post", color="#222", lw=1.6, zorder=3)
    ax.text(-0.15, Y_CLK + AMP / 2, "clk_cpu", ha="right", va="center",
            fontsize=11, fontweight="bold")

    # フェーズ列（ラベル付きボックス）
    ax.text(-0.15, PH_Y0 + PH_H / 2, "フェーズ", ha="right", va="center",
            fontsize=11, fontweight="bold")
    for k, ph in enumerate(phase_seq):
        ax.add_patch(Rectangle((k, PH_Y0), 1, PH_H, fc=PH_COLOR[ph],
                               ec=PH_EDGE[ph], lw=1.2, zorder=2))
        label = ph + ("\n(空打ち)" if (wb_prime_k is not None and k == wb_prime_k) else "")
        ax.text(k + 0.5, PH_Y0 + PH_H / 2, label, ha="center", va="center",
                fontsize=8.5, color="#333", zorder=3)

    # 命令ROMラッチ出力（無効/有効）
    ax.text(-0.15, VL_Y0 + VL_H / 2, "命令ROM\nラッチ出力", ha="right", va="center",
            fontsize=10, fontweight="bold")
    if valid_from > 0:
        ax.add_patch(Rectangle((0, VL_Y0), valid_from, VL_H, fc="#e2e2e2",
                               ec="#999", lw=1.0, zorder=2))
        ax.text(valid_from / 2, VL_Y0 + VL_H / 2, "無効", ha="center", va="center",
                fontsize=9, color="#777", zorder=3)
    ax.add_patch(Rectangle((valid_from, VL_Y0), N - valid_from, VL_H, fc="#d7f0df",
                           ec="#1a9c4e", lw=1.2, zorder=2))
    ax.text((valid_from + N) / 2, VL_Y0 + VL_H / 2, "有効（OPR/OPC 確定）",
            ha="center", va="center", fontsize=9, color="#157a3c", zorder=3)
    # 有効開始位置に矢印
    ax.annotate("", xy=(valid_from, VL_Y0 + VL_H + 0.05),
                xytext=(valid_from, VL_Y0 + VL_H + 0.5),
                arrowprops=dict(arrowstyle="->", color=note_color, lw=1.5))

    ax.text(-1.05, 4.72, title, ha="left", va="center", fontsize=12,
            fontweight="bold", color=note_color)
    ax.text(N + 0.05, VL_Y0 + VL_H / 2 + 0.55, note, ha="left", va="center",
            fontsize=9.5, color="#333",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=note_color, lw=1.3))

    # クロック番号
    for k in range(N):
        ax.text(k + 0.5, -0.15, str(k + 1), ha="center", va="top",
                fontsize=8, color="#999")

    ax.set_xlim(-1.7, N + 3.7)
    ax.set_ylim(-0.5, 4.9)
    ax.axis("off")


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.6))

# Before: FCH 始まり。1回目FCH(クロック1)で取りこぼし → クロック5(2回目FCH)で有効
draw_panel(
    ax1,
    phase_seq=["FCH", "DEC", "EXE", "WB", "FCH", "DEC", "EXE", "WB"],
    valid_from=4,
    title="Before：リセット後 FCH 始まり",
    note="1回目のFCHではラッチできず、\n2命令め（クロック5）からフェッチ成立\n→ 1命令遅れ。ジャンプで余分な命令が走る",
    note_color="#d33",
)

# After: WB(空打ち)始まり。クロック2のFCHで有効
draw_panel(
    ax2,
    phase_seq=["WB", "FCH", "DEC", "EXE", "WB", "FCH", "DEC", "EXE"],
    valid_from=1,
    title="After：リセット後 WB（空打ち）始まり",
    note="リセット後1クロックめをWB(空打ち)に。\n続くFCH（クロック2）で正しくラッチ\n→ 1命令めから実行できる",
    note_color="#1a9c4e",
    wb_prime_k=0,
)

fig.suptitle("リセット起動時のフェーズ・プライミング（FCH始まり vs WB始まり）",
             fontsize=13.5, fontweight="bold", y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.97])
out = "priming_timechart.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print("saved:", out)
