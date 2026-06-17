from machine import Pin, UART
import time

uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

p2 = Pin(2, Pin.IN)  # CH0
p3 = Pin(3, Pin.IN)  # CH1
p4 = Pin(4, Pin.IN)  # CH2
p5 = Pin(5, Pin.IN)  # CH3
p6 = Pin(6, Pin.IN)  # CH4
p7 = Pin(7, Pin.IN)  # CH5
p8 = Pin(8, Pin.IN)  # CH6
# p9 = Pin(9, Pin.IN)  # CH7

t_start = time.ticks_ms()
while True:
    t = time.ticks_diff(time.ticks_ms(), t_start)
    T = t / 1000  # 秒
#     uart.write("{},{},{},{}\n".format(T, p2.value(), p3.value(), p4.value()))
    uart.write("{:.1f},{},{},{},{},{},{},{}\n".format(T, p2.value(), p3.value(), p4.value(), p5.value(), p6.value(), p7.value(), p8.value()))

#     print(f"{t},{p2.value()},{p3.value()},{p4.value()},{p5.value()},{p6.value()},{p7.value()},{p8.value()}")

    time.sleep_ms(100)  # 10Hz サンプリング
