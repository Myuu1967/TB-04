import sys
import serial
import matplotlib.pyplot as plt

# TB-04 ver2 用 Pico 高速ロジアナ（PC側）。Pico側は forLogiAna.py
# 使い方: python logicAnalyzer.py [COMポート] [取り込む回数]
# 先にこれを起動 → TB-04 をリセットして走らせる。1回目＝最初の CALL の EXE 末、2回目＝RET の EXE 末
COM_PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM13'
N_CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 2
NAMES = ['CLK_CPU', '~WE_RAM', '~CS_RAM', 'MD5', 'CH4', 'CH5', 'CH6', 'CH7']

plt.rcParams['font.family'] = 'MS Gothic'

ser = serial.Serial(COM_PORT, 115200, timeout=1)


def decode(nch, words):
    """ワード列をサンプル列 [[ch0, ch1, ...], ...] に戻す（下位ビットが古い）"""
    mask = (1 << nch) - 1
    out = []
    for w in words:
        for k in range(32 // nch):
            v = (w >> (k * nch)) & mask
            out.append([(v >> c) & 1 for c in range(nch)])
    return out


caps = []
while len(caps) < N_CAP:
    line = ser.readline().decode(errors='ignore').strip()
    if line.startswith('READY'):
        print(line)
    if not line.startswith('CAP'):
        continue
    f = line.split(',')
    n, nch, ns = int(f[1]), int(f[2]), int(f[3])
    s = decode(nch, [int(x, 16) for x in f[4:]])
    caps.append((n, nch, ns, s))

    # 書込が成立しうる窓＝ ~WE_RAM と ~CS_RAM が同時に L
    both = [i for i, v in enumerate(s) if v[1] == 0 and v[2] == 0]
    print(f'--- 取込{n}  ({ns}ns/サンプル・t=0 は CLK↑ から約3サンプル後)')
    for i, v in enumerate(s):
        print(f'{i * ns:4d}ns  ' + '  '.join(f'{NAMES[c]}={v[c]}' for c in range(nch)))
    if both:
        md = sorted({s[i][3] for i in both}) if nch > 3 else []
        print(f'★ ~WE・~CS 同時L: {both[0] * ns}〜{both[-1] * ns}ns（{len(both) * ns}ns）  その間のMD5={md}')
    else:
        print('~WE・~CS の同時Lなし')

fig, axes = plt.subplots(caps[0][1], len(caps), sharex=True, squeeze=False, figsize=(5 * len(caps), 6))
for col, (n, nch, ns, s) in enumerate(caps):
    t = [i * ns for i in range(len(s))]
    for c in range(nch):
        ax = axes[c][col]
        ax.step(t, [v[c] for v in s], where='post')
        ax.set_ylim(-0.1, 1.1)
        ax.set_yticks([0, 1])
        if col == 0:
            ax.set_ylabel(NAMES[c])
    axes[0][col].set_title(f'取込{n}')
    axes[-1][col].set_xlabel('CLK↑ からの時間 [ns]')
fig.tight_layout()
fig.savefig('logicAnalyzer.png')
plt.show()
