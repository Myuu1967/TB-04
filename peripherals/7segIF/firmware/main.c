/*
 * 7segIF firmware  ―  TB-04 の 4bit OUT を 0..F の7セグ表示にデコード
 *
 * MCU        : CH32V003F4P6 (RISC-V, QingKe V2A)
 * Toolchain  : MounRiver Studio ＋ WCH 標準ペリフェラルライブラリ(SPL)
 * Display    : LTS-6960HR（コモンアノード・赤）
 *
 * 実配線（2026-07-20 ネットリストで確定）:
 *   入力  TB-04 OUT → J1:  D0=PC0  D1=PC1  D2=PC2  D3=PC3   … PORTC[3:0]
 *   出力  → 7セグ(各3.3K):  a=PD0 b=PD1 c=PD2 d=PD3 e=PD4 f=PD5 g=PD6 DP=PD7 … PORTD[7:0]
 *   コモンアノード → セグメントは MCU ピン LOW(0) で点灯。
 *
 * 注意（回路は問題なし・ソフト/書込側の制約）:
 *   - PD1(seg b) は SWIO。GPIO 使用中はライブデバッグ不可。再書込は
 *     WCH-Link のパワーサイクル or ダウンローダの「ByPass/解除」で対応。
 *   - PD7(seg DP) は既定 NRST。オプションバイト RST_MODE を GPIO 側に
 *     設定するまで DP は光らない。数字 0..F(a..g) は設定なしでも動作する。
 *     MounRiver では書込時のダウンロード設定 or WCHISPTool で RST_MODE を変更する。
 *
 * MounRiver での使い方:
 *   1. 新規に CH32V003F4P6 のプロジェクトを作成。
 *   2. 生成される User/main.c を本ファイルで置き換える。
 *   3. Peripheral(SPL) の GPIO/RCC が有効なテンプレートであること（既定で可）。
 */

#include "debug.h"   /* ch32v00x.h / GPIO / RCC などを取り込む標準テンプレートヘッダ */
#include <stdint.h>

/*
 * セグメントパターン。bit0=a, bit1=b, ... bit6=g, bit7=DP。
 * 「1 = 点灯」で定義（コモンカソード表記）。
 * 実出力はコモンアノードなので main で反転し 0=点灯 にする。DP(bit7) は常に消灯。
 */
static const uint8_t SEG_ON[16] = {
    0x3F, /* 0 : a b c d e f   */
    0x06, /* 1 : b c           */
    0x5B, /* 2 : a b d e g     */
    0x4F, /* 3 : a b c d g     */
    0x66, /* 4 : b c f g       */
    0x6D, /* 5 : a c d f g     */
    0x7D, /* 6 : a c d e f g   */
    0x07, /* 7 : a b c         */
    0x7F, /* 8 : a b c d e f g */
    0x6F, /* 9 : a b c d f g   */
    0x77, /* A : a b c e f g   */
    0x7C, /* b : c d e f g     */
    0x39, /* C : a d e f       */
    0x5E, /* d : b c d e g     */
    0x79, /* E : a d e f g     */
    0x71, /* F : a e f g       */
};

int main(void)
{
    GPIO_InitTypeDef GPIO_InitStructure = {0};

    SystemCoreClockUpdate();

    /* GPIO ポート C / D のクロック供給 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC | RCC_APB2Periph_GPIOD, ENABLE);

    /*
     * PORTC PC0..PC3 = 入力フローティング
     *   TB-04 の 74HC 出力（プッシュプル・5V）が常にドライブするので pull 不要。
     *   断線時にブランク固定したいなら GPIO_Mode_IPD（内部プルダウン）に変更。
     */
    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_IN_FLOATING;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_10MHz;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    /*
     * PORTD PD0..PD7 = 出力プッシュプル 10MHz
     *   off 状態は High 出力＝アノードもカソードも VDD 付近で消灯。
     */
    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 | GPIO_Pin_3
                                  | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_10MHz;
    GPIO_Init(GPIOD, &GPIO_InitStructure);

    /* 起動時は全消灯（コモンアノード＝全 High） */
    GPIO_Write(GPIOD, 0x00FF);

    while (1)
    {
        uint8_t v = (uint8_t)(GPIO_ReadInputData(GPIOC) & 0x0F);  /* D0..D3 → 0..15 */
        GPIO_Write(GPIOD, (uint16_t)(uint8_t)~SEG_ON[v]);         /* 0=点灯 に反転出力 */
    }
}
