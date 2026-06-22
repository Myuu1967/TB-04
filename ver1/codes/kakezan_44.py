#!/usr/bin/env python3
"""かけ算 四四（4×4）— 足し算の繰り返しで全組み合わせを計算する純Pythonプロトタイプ

TB-04（4bit CPU）への移植を見据えたアルゴリズム確認用。
かけ算演算子( * )は使わず、i を j 回足し込むことで i×j を求める。
ハードの制約（レジスタ4本・命令16個・4bit幅）はここでは反映しない。

参考: 4bit CPU の OUT ポートは 0〜15 しか表せないため、
      積が16以上になる場合に実機で見える値（&0xF）も併記する。
"""

N = 4  # 1〜N の段（四四なら 4）


def mul_by_add(i: int, j: int) -> int:
    """i×j を「i を j 回足す」繰り返し加算で求める。"""
    acc = 0
    for _ in range(j):   # ← CPU の内側ループ（j 回 ADD acc, i）に対応
        acc += i
    return acc


def main() -> None:
    print(f"=== かけ算 {N}{N}（{N}×{N}）足し算版 ===\n")
    for i in range(1, N + 1):        # 外側ループ: 被乗数 i = 1..N
        for j in range(1, N + 1):    # 内側ループ: 乗数   j = 1..N
            p = mul_by_add(i, j)
            cpu_out = p & 0xF        # 4bit CPU の OUT で見える値
            note = f"  -> 4bit OUT={cpu_out:2d}" if p > 15 else ""
            print(f"{i} x {j} = {p:2d}{note}")
        print()


if __name__ == "__main__":
    main()
