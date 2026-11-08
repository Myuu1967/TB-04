"""TB-04 ver2 簡易アセンブラ／ローダー・逆アセンブラ

固定2語命令（byte1=opcode プレフィックス／byte2=オペランド）をエンコードする。
本格アセンブラ（tanuki_asm ver2）は論理凍結後。ここは論理検証用の最小ヘルパー。

使い方（ラベル対応の2パス）:
    from asm import Asm
    p = Asm()
    p.MOVI(0, 0)          # R0 = 0
    p.label('loop')
    p.OUT(0, 0)           # OUT[0] = R0
    p.ADDI(0, 1)          # R0 += 1  （Cin=C_prev のため CLC を前置）
    p.JMP('loop')
    rom = p.assemble()    # bytes 列（各命令2バイト）

Addr/分岐先はラベル文字列 or 数値（バイト番地）で指定可。
アドレスは「命令インデックス×2」＝命令は必ず2バイト固定。
"""

# opcode プレフィックス（ドラフト§5）
_SINGLE = {'NOP': 0x0, 'MOV': 0x1, 'MOVI': 0x2, 'LD': 0x3, 'ST': 0x4, 'STI': 0x5}
_E = {'JMP': 0x0, 'JC': 0x1, 'JNC': 0x2, 'JZ': 0x3, 'JNZ': 0x4,
      'CALL': 0x5, 'RET': 0x6, 'PUSH': 0x8, 'POP': 0x9,
      'IN': 0xA, 'OUT': 0xB, 'OUTI': 0xC}
_F = {'CP': 0x0, 'AND': 0x1, 'OR': 0x2, 'XOR': 0x3, 'NOT': 0x4,
      'SHL': 0x5, 'SHR': 0x6, 'ROL': 0x7, 'ROR': 0x8,
      'ADD': 0x9, 'ADDI': 0xA, 'SUB': 0xB, 'SUBI': 0xC, 'CLC': 0xD, 'SEC': 0xE}


class Asm:
    def __init__(self):
        self.prog = []      # [(op, args), ...]  1要素=1命令(2バイト)
        self.labels = {}

    def label(self, name):
        self.labels[name] = len(self.prog) * 2   # 現在のバイト番地
        return self

    def _add(self, op, *args):
        self.prog.append((op, args))
        return self

    # --- 単独ニブル ---
    def NOP(self):              return self._add('NOP')
    def MOV(self, ri, rj):      return self._add('MOV', ri, rj)
    def MOVI(self, ri, im):     return self._add('MOVI', ri, im)
    def LD(self, ri, addr):     return self._add('LD', ri, addr)
    def ST(self, addr, ri):     return self._add('ST', addr, ri)
    def STI(self, addr, im):    return self._add('STI', addr, im)
    # --- E系 ---
    def JMP(self, addr):        return self._add('JMP', addr)
    def JC(self, addr):         return self._add('JC', addr)
    def JNC(self, addr):        return self._add('JNC', addr)
    def JZ(self, addr):         return self._add('JZ', addr)
    def JNZ(self, addr):        return self._add('JNZ', addr)
    def CALL(self, addr):       return self._add('CALL', addr)
    def RET(self):              return self._add('RET')
    def HALT(self):             return self._add('HALT')   # JMP $ へ展開
    def PUSH(self, ri):         return self._add('PUSH', ri)
    def POP(self, ri):          return self._add('POP', ri)
    def IN(self, ri, port):     return self._add('IN', ri, port)
    def OUT(self, port, ri):    return self._add('OUT', port, ri)
    def OUTI(self, port, im):   return self._add('OUTI', port, im)
    # --- F系 ---
    def CP(self, ri, rj):       return self._add('CP', ri, rj)
    def AND(self, ri, rj):      return self._add('AND', ri, rj)
    def OR(self, ri, rj):       return self._add('OR', ri, rj)
    def XOR(self, ri, rj):      return self._add('XOR', ri, rj)
    def NOT(self, ri):          return self._add('NOT', ri)
    def SHL(self, ri):          return self._add('SHL', ri)
    def SHR(self, ri):          return self._add('SHR', ri)
    def ROL(self, ri):          return self._add('ROL', ri)
    def ROR(self, ri):          return self._add('ROR', ri)
    def ADD(self, ri, rj):      return self._add('ADD', ri, rj)
    def ADDI(self, ri, im):     return self._add('ADDI', ri, im)
    def SUB(self, ri, rj):      return self._add('SUB', ri, rj)
    def SUBI(self, ri, im):     return self._add('SUBI', ri, im)
    def CLC(self):              return self._add('CLC')
    def SEC(self):              return self._add('SEC')
    # --- 生バイト（表示用の単語など）---
    def DATA(self, b1, b2):     return self._add('DATA', b1, b2)

    # ------------------------------------------------------------------
    def _resolve(self, a):
        if isinstance(a, str):
            if a not in self.labels:
                raise KeyError(f'未定義ラベル: {a}')
            return self.labels[a]
        return a & 0xFF

    def assemble(self):
        out = []
        for idx, (op, args) in enumerate(self.prog):
            b1, b2 = encode(op, args, addr=idx * 2, resolve=self._resolve)
            out.append(b1 & 0xFF)
            out.append(b2 & 0xFF)
        return out


def encode(op, args, addr=0, resolve=None):
    """(byte1, byte2) を返す。resolve はラベル→番地の解決関数。"""
    if resolve is None:
        resolve = lambda x: x & 0xFF

    if op == 'DATA':                       # 擬似命令＝生バイト2つ
        return args[0] & 0xFF, args[1] & 0xFF

    if op == 'HALT':                       # 擬似命令＝JMP 自番地
        return (PFX(0xE) | _E['JMP']), addr & 0xFF

    if op in _SINGLE:
        opc = _SINGLE[op]
        if op == 'NOP':
            return (opc << 4), 0x00
        if op == 'MOV':
            ri, rj = args
            return (opc << 4), ((ri & 7) << 4) | (rj & 7)
        if op == 'MOVI':
            ri, im = args
            return (opc << 4) | (im & 0xF), (ri & 7) << 4
        if op == 'LD':
            ri, a = args
            return (opc << 4) | (ri & 7), resolve(a)
        if op == 'ST':
            a, ri = args
            return (opc << 4) | (ri & 7), resolve(a)
        if op == 'STI':
            a, im = args
            return (opc << 4) | (im & 0xF), resolve(a)

    if op in _E:
        sub = _E[op]
        b1 = PFX(0xE) | sub
        if op in ('JMP', 'JC', 'JNC', 'JZ', 'JNZ', 'CALL'):
            return b1, resolve(args[0])
        if op == 'RET':
            return b1, 0x00
        if op in ('PUSH', 'POP'):
            return b1, (args[0] & 7) << 4
        if op == 'IN':                     # IN Ri,port → {Ri[6:4], port[1:0]}
            r, port = args
            return b1, ((r & 7) << 4) | (port & 3)
        if op == 'OUT':                    # OUT port,Ri → {Ri[6:4], port[1:0]}
            port, r = args
            return b1, ((r & 7) << 4) | (port & 3)
        if op == 'OUTI':                   # {port[5:4], Im4[3:0]}
            port, im = args
            return b1, ((port & 3) << 4) | (im & 0xF)

    if op in _F:
        sub = _F[op]
        b1 = PFX(0xF) | sub
        if op in ('CP', 'AND', 'OR', 'XOR', 'ADD', 'SUB'):   # {Ri[6:4], Rj[2:0]}
            ri, rj = args
            return b1, ((ri & 7) << 4) | (rj & 7)
        if op in ('NOT', 'SHL', 'SHR', 'ROL', 'ROR'):        # Ri[6:4]
            return b1, (args[0] & 7) << 4
        if op in ('ADDI', 'SUBI'):                            # {Ri[6:4], Im4[3:0]}
            ri, im = args
            return b1, ((ri & 7) << 4) | (im & 0xF)
        if op in ('CLC', 'SEC'):
            return b1, 0x00

    raise ValueError(f'未知の命令: {op}')


def PFX(nib):
    return (nib & 0xF) << 4


# ---------------------------------------------------------------------
# 逆アセンブラ（トレース表示用）
# ---------------------------------------------------------------------
_E_NAMES = {v: k for k, v in _E.items()}
_F_NAMES = {v: k for k, v in _F.items()}
_S_NAMES = {v: k for k, v in _SINGLE.items()}


def disasm(byte1, byte2):
    hi = (byte1 >> 4) & 0xF
    ri_b2 = (byte2 >> 4) & 7
    rj_b2 = byte2 & 7
    if hi == 0xE:
        sub = byte1 & 0xF
        name = _E_NAMES.get(sub, f'E{sub:X}?')
        if name in ('JMP', 'JC', 'JNC', 'JZ', 'JNZ', 'CALL'):
            return f'{name} {byte2:#04x}'
        if name == 'RET':
            return 'RET'
        if name in ('PUSH', 'POP'):
            return f'{name} R{ri_b2}'
        if name in ('IN', 'OUT'):
            return f'{name} R{ri_b2},p{byte2 & 3}'
        if name == 'OUTI':
            return f'OUTI p{(byte2 >> 4) & 3},{byte2 & 0xF}'
        return name
    if hi == 0xF:
        sub = byte1 & 0xF
        name = _F_NAMES.get(sub, f'F{sub:X}?')
        if name in ('CP', 'AND', 'OR', 'XOR', 'ADD', 'SUB'):
            return f'{name} R{ri_b2},R{rj_b2}'
        if name in ('ADDI', 'SUBI'):
            return f'{name} R{ri_b2},{byte2 & 0xF}'
        if name in ('NOT', 'SHL', 'SHR', 'ROL', 'ROR'):
            return f'{name} R{ri_b2}'
        return name
    name = _S_NAMES.get(hi, f'S{hi:X}?')
    if name == 'NOP':
        return 'NOP'
    if name == 'MOV':
        return f'MOV R{ri_b2},R{rj_b2}'
    if name == 'MOVI':
        return f'MOVI R{ri_b2},{byte1 & 0xF}'
    if name == 'LD':
        return f'LD R{byte1 & 7},[{byte2:#04x}]'
    if name == 'ST':
        return f'ST [{byte2:#04x}],R{byte1 & 7}'
    if name == 'STI':
        return f'STI [{byte2:#04x}],{byte1 & 0xF}'
    return name


def dump_rom(rom, width=8):
    for i in range(0, len(rom), 2):
        b1 = rom[i]
        b2 = rom[i + 1] if i + 1 < len(rom) else 0
        print(f'  {i:#04x}: {b1:02X} {b2:02X}   {disasm(b1, b2)}')
