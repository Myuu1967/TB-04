"""tanuki 4bit CPU アセンブラヘルパー・逆アセンブラ

命令エンコード:
  D[3:0] = OPC[3:0]  (4bit opcode, 下位ニブル)
  D[7:4] = OPR[3:0]  (4bit operand, 上位ニブル)

レジスタ-レジスタ命令: OPR = (i << 2) | j
即値/アドレス命令:     OPR = Im or Addr
"""

# ---------- アセンブラ関数 ----------

def NOP():          return 0x00
def MOV(i, j):      return (((i & 3) << 2) | (j & 3)) << 4 | 0x1
def MOVI(im):       return (im & 0xF) << 4 | 0x2
def OUT(i):         return ((i & 3) << 2) << 4 | 0x3
def OUTI(im):       return (im & 0xF) << 4 | 0x4
def IN(i):          return ((i & 3) << 2) << 4 | 0x5
def JMP(addr):      return (addr & 0xF) << 4 | 0x6
def JNC(addr):      return (addr & 0xF) << 4 | 0x7
def JZ(addr):       return (addr & 0xF) << 4 | 0x8
def AND(i, j):      return (((i & 3) << 2) | (j & 3)) << 4 | 0x9
def OR(i, j):       return (((i & 3) << 2) | (j & 3)) << 4 | 0xA
def XOR(i, j):      return (((i & 3) << 2) | (j & 3)) << 4 | 0xB
def ADD(i, j):      return (((i & 3) << 2) | (j & 3)) << 4 | 0xC
def ADDI(im):       return (im & 0xF) << 4 | 0xD
def SUB(i, j):      return (((i & 3) << 2) | (j & 3)) << 4 | 0xE
def SUBI(im):       return (im & 0xF) << 4 | 0xF

# ---------- 逆アセンブラ ----------

def disasm(byte):
    """1バイト命令を文字列に変換"""
    opc = byte & 0xF
    opr = (byte >> 4) & 0xF
    ri  = (opr >> 2) & 3
    rj  = opr & 3

    if   opc == 0x0: return "NOP"
    elif opc == 0x1: return f"MOV   R{ri}, R{rj}"
    elif opc == 0x2: return f"MOVI  R0, {opr}"
    elif opc == 0x3: return f"OUT   R{ri}"
    elif opc == 0x4: return f"OUTI  {opr}"
    elif opc == 0x5: return f"IN    R{ri}"
    elif opc == 0x6: return f"JMP   0x{opr:X}"
    elif opc == 0x7: return f"JNC   0x{opr:X}"
    elif opc == 0x8: return f"JZ    0x{opr:X}"
    elif opc == 0x9: return f"AND   R{ri}, R{rj}"
    elif opc == 0xA: return f"OR    R{ri}, R{rj}"
    elif opc == 0xB: return f"XOR   R{ri}, R{rj}"
    elif opc == 0xC: return f"ADD   R{ri}, R{rj}"
    elif opc == 0xD: return f"ADDI  R0, {opr}"
    elif opc == 0xE: return f"SUB   R{ri}, R{rj}"
    elif opc == 0xF: return f"SUBI  R0, {opr}"
    return "???"

def dump_rom(rom):
    """ROM 内容をリスト表示"""
    print("Addr | Hex | Disassembly")
    print("-----|-----|------------------")
    for i, b in enumerate(rom[:16]):
        print(f"  {i:X}  | {b:02X}  | {disasm(b)}")
