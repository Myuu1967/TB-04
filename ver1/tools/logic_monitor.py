import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation

COM_PORT = 'COM13'
BAUD     = 115200
WINDOW   = 100

ser = serial.Serial(COM_PORT, BAUD, timeout=0.05)

# times, ch0, ch1, ch2 = [], [], [], []
times, ch0, ch1, ch2, ch3, ch4, ch5, ch6 = [], [], [], [], [], [], [], []
_buf = ''  # 受信途中の行バッファ

fig, (ax0, ax1, ax2, ax3, ax4, ax5, ax6) = plt.subplots(7, 1, sharex=True, figsize=(10, 8))
fig.suptitle('Logic Monitor')

ax0.set_ylabel('Clock')
ax0.set_ylim(-0.1, 1.1)
ax0.set_yticks([0, 1])

ax1.set_ylabel('CH0')
ax1.set_ylim(-0.1, 1.1)
ax1.set_yticks([0, 1])

ax2.set_ylabel('CH1')
ax2.set_ylim(-0.1, 1.1)
ax2.set_yticks([0, 1])

ax3.set_ylabel('CH2')
ax3.set_ylim(-0.1, 1.1)
ax3.set_yticks([0, 1])

ax4.set_ylabel('CH3')
ax4.set_ylim(-0.1, 1.1)
ax4.set_yticks([0, 1])

ax5.set_ylabel('CH4')
ax5.set_ylim(-0.1, 1.1)
ax5.set_yticks([0, 1])

ax6.set_ylabel('CH5')
ax6.set_ylim(-0.1, 1.1)
ax6.set_yticks([0, 1])
ax6.set_xlabel('Time [s]')

# 起動時に Line2D オブジェクトを一度だけ作る
line0, = ax0.step([], [], where='post', color='tab:blue')
line1, = ax1.step([], [], where='post', color='tab:orange')
line2, = ax2.step([], [], where='post', color='tab:green')
line3, = ax3.step([], [], where='post', color='tab:red')
line4, = ax4.step([], [], where='post', color='tab:cyan')
line5, = ax5.step([], [], where='post', color='tab:purple')
line6, = ax6.step([], [], where='post', color='tab:brown')

fig.tight_layout()


def update(frame):
    global _buf

    # バッファにある全データを読み、最新の1サンプルだけ使う
    raw = ser.read(ser.in_waiting or 1)
    _buf += raw.decode(errors='ignore')

    lines = _buf.split('\n')
    _buf = lines[-1]  # 未完成の末尾行を次回に持ち越す
    complete = [l.strip() for l in lines[:-1] if l.strip()]

    if not complete:
        return

    line = complete[-1]  # 最新行だけ使う（古いものは捨てる）
    parts = line.split(',')
    if len(parts) != 8:
        return
    try:
        t = float(parts[0])
        v0, v1, v2, v3, v4, v5, v6 = (int(p) for p in parts[1:8])
    except ValueError:
        return

    times.append(t)
    ch0.append(v0)
    ch1.append(v1)
    ch2.append(v2)
    ch3.append(v3)
    ch4.append(v4)
    ch5.append(v5)
    ch6.append(v6)

    t_w  = times[-WINDOW:]
    c0_w = ch0[-WINDOW:]
    c1_w = ch1[-WINDOW:]
    c2_w = ch2[-WINDOW:]
    c3_w = ch3[-WINDOW:]
    c4_w = ch4[-WINDOW:]
    c5_w = ch5[-WINDOW:]
    c6_w = ch6[-WINDOW:]

    line0.set_data(t_w, c0_w)
    line1.set_data(t_w, c1_w)
    line2.set_data(t_w, c2_w)
    line3.set_data(t_w, c3_w)
    line4.set_data(t_w, c4_w)
    line5.set_data(t_w, c5_w)
    line6.set_data(t_w, c6_w)

    if len(t_w) >= 2:
        for ax in (ax0, ax1, ax2, ax3, ax4, ax5, ax6):
            ax.set_xlim(t_w[0], t_w[-1])


ani = animation.FuncAnimation(fig, update, interval=50, cache_frame_data=False)
plt.show()
