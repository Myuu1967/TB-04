# TB-04 ver2 用 Pico 高速ロジアナ（送信側）。PC側は同じディレクトリの logicAnalyzer.py
from machine import Pin, UART
import machine
import rp2

# PIOで125MHz(8ns)サンプリング。トリガー後の64サンプル(512ns)を取り込んでUARTへ送る
# トリガー＝ CH2(~CS_RAM)=L のあいだに CH0(CLK_CPU) が L→H（＝RAMを触る命令のEXE末）
# 入力は分圧抵抗（1kΩ + 2kΩ）経由。RC で 10ns 程度なまる点に注意

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

NCH = 4                      # 4 か 8（32bit を割り切れる数）
pins = [Pin(2 + i, Pin.IN) for i in range(NCH)]
# CH0 GP2 = CLK_CPU  (U501-8)
# CH1 GP3 = ~WE_RAM  (U1101-21)
# CH2 GP4 = ~CS_RAM  (U1101-18)
# CH3 GP5 = MD5      (U1101-15)   06→B6 で 0→1 に変わるビット

WORDS = 8                    # RX FIFO を結合した深さ
SPW = 32 // NCH              # 1ワードあたりのサンプル数


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32,
             fifo_join=rp2.PIO.JOIN_RX)
def capture():
    wait(0, pin, 2)          # ~CS_RAM = L（EXE中）
    wait(0, pin, 0)          # CLK_CPU = L（EXE中間）
    wait(1, pin, 0)          # CLK_CPU ↑（EXE末）
    wrap_target()
    in_(pins, 4)             # ＝NCH（PIO内ではグローバル変数を使えない）。FIFOが満杯になると止まる＝最初の WORDS 語が連続サンプル
    wrap()


freq = machine.freq()        # 既定 125MHz → 8ns/サンプル
ns = 1_000_000_000 // freq
n = 0
uart.write("READY,{},{},{}\n".format(NCH, ns, WORDS * SPW))
while True:
    sm = rp2.StateMachine(0, capture, freq=freq, in_base=pins[0])
    sm.active(1)
    words = [sm.get() for _ in range(WORDS)]
    sm.active(0)
    while sm.rx_fifo():
        sm.get()
    n += 1
    uart.write("CAP,{},{},{},{}\n".format(n, NCH, ns, ",".join("{:08x}".format(w) for w in words)))
