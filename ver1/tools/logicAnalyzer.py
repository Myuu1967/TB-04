import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation

ser = serial.Serial('COM13', 115200, timeout=1)  # COMポートは要変更

times, ch0, ch1 , ch2 = [], [], [], []
# times, ch0, ch1, ch2, ch3, ch4, ch5, ch6, ch7 = [], [], [], [], [], [], [], [], []

fig, ax = plt.subplots()

def update(frame):
    line = ser.readline().decode().strip()
    if ',' not in line:
        return
    t, v0, v1, v2 = line.split(',')
    # t, v0, v1, v2, v3, v4, v5, v6, v7 = line.split(',')
    times.append(int(t))
    ch0.append(int(v0))
    ch1.append(int(v1))
    ch2.append(int(v2))
    # ch3.append(int(v3))
    # ch4.append(int(v4))
    # ch5.append(int(v5))
    # ch6.append(int(v6))
    # ch7.append(int(v7))

    ax.clear()
    ax.step(times[-100:], ch0[-100:], label='D6 (ROM出力)')
    ax.step(times[-100:], ch1[-100:], label='Q6 (ラッチ後)', linestyle='--')
    ax.step(times[-100:], ch2[-100:], label='CH2')
    # ax.step(times[-200:], ch3[-200:], label='CH3')
    # ax.step(times[-200:], ch4[-200:], label='CH4')
    # ax.step(times[-200:], ch5[-200:], label='CH5')
    # ax.step(times[-200:], ch6[-200:], label='CH6')
    # ax.step(times[-200:], ch7[-200:], label='CH7')
    # ax.legend()
    ax.set_ylim(-0.1, 1.5)

ani = animation.FuncAnimation(fig, update, interval=1)
plt.show()