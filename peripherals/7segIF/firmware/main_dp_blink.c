/*
 * 7segIF firmware（お遊び版）  ―  数字表示 ＋ DP を 0.5秒ごとに点滅
 *
 * MCU        : CH32V003F4P6 (RISC-V)
 * Toolchain  : MounRiver Studio ＋ WCH 標準ペリフェラルライブラリ(SPL)
 * Display    : LTS-6960HR（コモンアノード・赤）
 *
 * 通常版 main.c との違い:
 *   - a..g（数字 0..F）は入力に追従してリアルタイム表示（同じ）。
 *   - DP(PD7) だけ 0.5秒周期で点滅させる。
 *   - 表示を止めないよう 10ms 刻みでループし、50回(=500ms)ごとに DP をトグル。
 *
 * ※ main.c と本ファイルは両方 main() を持つ。ビルドに含めるのは
 *   どちらか一方だけにすること（片方をプロジェクトのビルド対象から除外）。
 *
 * ※ DP(PD7) は既定 NRST。オプションバイト RST_MODE を GPIO 側に設定するまで
 *   DP は光らない（＝この点滅も見えない）。MounRiverの書込設定 or WCHISPTool で変更する。
 *
 * 実配線: 入力 D0=PC0..D3=PC3 / 出力 a=PD0 b=PD1 c=PD2 d=PD3 e=PD4 f=PD5 g=PD6 DP=PD7
 *         コモンアノード → セグメントは MCU ピン LOW(0) で点灯。
 */

#include "debug.h"
#include <stdint.h>

/* bit0=a..bit6=g,bit7=DP、1=点灯（コモンカソード表記）。出力時に反転する。 */
static const uint8_t SEG_ON[16] = {
    0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, /* 0-7 */
    0x7F, 0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71, /* 8-F */
};

#define DP_BIT      0x80u   /* PD7 = DP */
#define STEP_MS     10u     /* 表示更新の刻み */
#define BLINK_STEPS 50u     /* 10ms × 50 = 500ms でトグル */

int main(void)
{
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    uint8_t  dp_on = 0;
    uint16_t tick  = 0;

    SystemCoreClockUpdate();
    Delay_Init();

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC | RCC_APB2Periph_GPIOD
                         | RCC_APB2Periph_AFIO, ENABLE);

    /* PD1(seg b) の SDI(単線デバッグ)を無効化して GPIO に開放（詳細は main.c 参照） */
    GPIO_PinRemapConfig(GPIO_Remap_SDI_Disable, ENABLE);

    /* PC0..PC3 = 入力フローティング（TB-04 の 74HC 出力が常時ドライブ） */
    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_IN_FLOATING;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_10MHz;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    /* PD0..PD7 = 出力プッシュプル */
    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3
                                  | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_10MHz;
    GPIO_Init(GPIOD, &GPIO_InitStructure);

    GPIO_Write(GPIOD, 0x00FF);   /* 起動時 全消灯 */

    while (1)
    {
        uint8_t v   = (uint8_t)(GPIO_ReadInputData(GPIOC) & 0x0F);
        uint8_t out = (uint8_t)~SEG_ON[v];   /* bit7=1 → DP は消灯状態 */

        if (dp_on) {
            out &= (uint8_t)~DP_BIT;         /* DP 点灯（bit7=0） */
        }
        GPIO_Write(GPIOD, out);

        Delay_Ms(STEP_MS);
        if (++tick >= BLINK_STEPS) {
            tick  = 0;
            dp_on ^= 1;                       /* 0.5秒ごとに DP をトグル */
        }
    }
}
