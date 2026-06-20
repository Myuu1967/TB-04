# -*- coding: utf-8 -*-
"""
TB-04 ver.1 ブログ完成編 図用
基本の4フェーズ・1命令サイクルのタイムチャート（理想化模式波形）
clk_cpu と 74HC238 の4本ワンホット出力 FCH/DEC/EXE/WB を表示し、
各フェーズで起きる動作を注釈する。
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

# --- 日本語フォント設定 ---
for _f in ["Meiryo", "Yu Gothic", "MS Gothic", "Noto Sans CJK JP", "MS PGothic"]:
    try:
        font_manager.findfont(_f, fallback_to_default=False)
        plt.rcParams["font.family"] = _f
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

N = 5  # 表示クロック数（FCH DEC EXE WB | 次FCH）

def step_xy(values):
    """各クロック区間 [k,k+1) の値リストから where='post' 用の x,y を作る"""
    x = list(range(len(values) + 1))
    y = list(values) + [values[-1]]
    return x, y

# クロック（各整数で立上り、前半Highの方形波）
clk_x, clk_y = [], []
for k in range(N):
    clk_x += [k, k + 0.5]
    clk_y += [1, 0]
clk_x += [N]
clk_y += [0]

# 4フェーズ（ワンホット）。clk k の位相 = k%4
phases = {
    "FCH": [1 if k % 4 == 0 else 0 for k in range(N)],
    "DEC": [1 if k % 4 == 1 else 0 for k in range(N)],
    "EXE": [1 if k % 4 == 2 else 0 for k in range(N)],
    "WB":  [1 if k % 4 == 3 else 0 for k in range(N)],
}

# 配置（上から）
rows = ["clk_cpu", "FCH", "DEC", "EXE", "WB"]
y_base = {"clk_cpu": 8.0, "FCH": 6.4, "DEC": 4.9, "EXE": 3.4, "WB": 1.9}
amp = 1.0

fig, ax = plt.subplots(figsize=(11, 6.6))

# フェーズごとの薄い縦帯
band_colors = {0: "#fde9e9", 1: "#e9f3fd", 2: "#e9fbef", 3: "#fdf6e3"}
for k in range(N):
    c = band_colors[k % 4]
    a = 0.7 if k < 4 else 0.35  # 次命令側は薄く
    ax.axvspan(k, k + 1, color=c, alpha=a, zorder=0)

# クロック境界の点線
for k in range(N + 1):
    ax.axvline(k, color="0.7", lw=0.8, ls="--", zorder=1)

# クロック波形
ax.step([x for x in clk_x], [y_base["clk_cpu"] + amp * v for v in clk_y],
        where="post", color="#222", lw=1.8, zorder=3)

# フェーズ波形
ph_color = {"FCH": "#d33", "DEC": "#1769c7", "EXE": "#1a9c4e", "WB": "#c79a16"}
for name, vals in phases.items():
    x, y = step_xy(vals)
    ax.step(x, [y_base[name] + amp * v for v in y], where="post",
            color=ph_color[name], lw=2.0, zorder=3)

# 左ラベル
for name in rows:
    ax.text(-0.15, y_base[name] + amp / 2, name, ha="right", va="center",
            fontsize=12, fontweight="bold")

# 1命令サイクルのブラケット
ybr = 9.5
ax.annotate("", xy=(0, ybr), xytext=(4, ybr),
            arrowprops=dict(arrowstyle="<->", color="#444", lw=1.5))
ax.text(2.0, ybr + 0.18, "1命令サイクル（4クロック）", ha="center", va="bottom",
        fontsize=12, fontweight="bold", color="#444")
ax.text(4.5, ybr, "次命令…", ha="center", va="center", fontsize=10, color="#888")

# 各フェーズの動作注釈
notes = {
    0: ("FCH", "命令ROMを読出し\n74HC273でラッチ"),
    1: ("DEC", "デコーダROMで\n制御信号・alu_code確定"),
    2: ("EXE", "ALU演算→フラグ(74HC74)\nラッチ／(改造後)レジスタ書込"),
    3: ("WB", "(本来の)レジスタ書込\nPCインクリメント"),
}
for k, (ph, txt) in notes.items():
    ax.text(k + 0.5, 0.7, txt, ha="center", va="top", fontsize=9.5,
            color="#333",
            bbox=dict(boxstyle="round,pad=0.35", fc="white",
                      ec=ph_color[ph], lw=1.3))

ax.set_xlim(-0.9, 5.05)
ax.set_ylim(-1.7, 10.2)
ax.axis("off")
ax.set_title("基本の4フェーズ・1命令サイクルのタイムチャート（模式図）",
             fontsize=13, fontweight="bold", pad=10)

fig.tight_layout()
out = "4phase_timechart.png"
fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print("saved:", out)
