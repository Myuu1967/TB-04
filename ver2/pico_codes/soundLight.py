# soundLight.py — TB-04 ver2「音と光」デモの Pico 側（MicroPython）
#
# TB-04 の OUT0（4bit）を読んで、音（PWM）と色（NeoPixel）に変えるだけ。
# 曲・音の長さ・テンポはすべて TB-04 の ROM（sim/programs.py の melody）が持つ。
# Pico は判断も記憶もしない＝昔の PSG（音源チップ）と同じ役割。
#
#   OUT0 = 0      → 消音・消灯
#   OUT0 = 1〜15  → ド(C4)〜ド(C6)（ハ長調の白鍵・2オクターブ）
#
# 配線（入力は 5V 系なので 1kΩ + 2kΩ で分圧して Pico へ。GND は共通）
#   GP2 ← OUT0 bit0 / GP3 ← bit1 / GP4 ← bit2 / GP5 ← bit3
#   GP15 → 圧電スピーカー（または小型アンプ）
#   GP16 → NeoPixel（WS2812）のデータ。数は N_LED

from machine import Pin, PWM
import neopixel
import time

N_LED = 8
pins = [Pin(n, Pin.IN, Pin.PULL_DOWN) for n in (2, 3, 4, 5)]
spk = PWM(Pin(15))
np = neopixel.NeoPixel(Pin(16), N_LED)

# ド〜ド（C4〜C6）の白鍵 15音（Hz）。添字 = OUT0 の値
FREQ = [0, 262, 294, 330, 349, 392, 440, 494,
        523, 587, 659, 698, 784, 880, 988, 1047]
# 音名ごとの色（ド=赤 → シ=紫の虹）。上のオクターブは同じ色で明るく
COLOR = [(255, 0, 0), (255, 128, 0), (255, 255, 0), (0, 255, 0),
         (0, 255, 255), (0, 0, 255), (160, 0, 255)]


def read_out0():
    """OUT0 を読む。377 は4bitを同時に変えるが、念のため2回続けて同じ値になるまで読む。"""
    while True:
        a = sum(p.value() << i for i, p in enumerate(pins))
        b = sum(p.value() << i for i, p in enumerate(pins))
        if a == b:
            return a


def play(v):
    if v == 0:
        spk.duty_u16(0)
        np.fill((0, 0, 0))
    else:
        spk.freq(FREQ[v])
        spk.duty_u16(32768)
        r, g, b = COLOR[(v - 1) % 7]
        k = 1 if v >= 8 else 4                    # 低いオクターブは暗め
        np.fill((r // k, g // k, b // k))
    np.write()


last = -1
while True:
    v = read_out0()
    if v != last:                                 # 値が変わったときだけ鳴らし直す
        play(v)
        last = v
    time.sleep_us(200)
