# Parse SIM_* class: ctor tables, Get*Adrs tables, program bytes.
# Capstone prints immediates as decimal below 16, hex above -> _num handles both.
import struct, re
import lib

def _num(s):
    s=s.strip()
    return int(s,16) if s.startswith(('0x','-0x')) else int(s)

def disasm_meth(cls, meth):
    md=lib.md(); md.detail=True
    a=lib.load_exports()[cls+'::'+meth]
    s,e=lib.func(a)
    return s,e,[i for i in md.disasm(lib.Z[s:e],s)]

def program(cls):
    tab,fsp,pls=lib.pairs()[cls]
    render=[p for p in pls if p[1]==0]
    if not render: raise ValueError('No render program for '+cls)
    segments=render[0][3]
    # JDMLT_B has an empty bank-A stub and its real implementation in bank B.
    primary=max(segments, key=lambda seg: seg[1])
    b0,ln,c0,dA=primary
    peer=next((seg for seg in segments if seg is not primary and seg[1]==ln),primary)
    b1,_,c1,dB=peer
    return ln, lib.be(lib.Z[dA:dA+((ln+3)&~3)]), lib.be(lib.Z[dB:dB+((ln+3)&~3)]), tab, b0, b1

def ctor_addr(cls):
    _,e,code=disasm_meth(cls,'Init()')
    seen=False
    for i in code:
        if i.mnemonic=='bl':
            if seen: return int(i.op_str.lstrip('#'),16)
            seen=True

HEX=r'-?(?:0x)?[0-9a-fA-F]+'
def _rd(i):
    if not i.operands: return None
    o=i.operands[0]
    import capstone
    if o.type==capstone.arm64.ARM64_OP_REG: return i.reg_name(o.reg)
    return None

def parse_ctor(cls):
    """Emulate ctor constant propagation.
      coefs:  {objoff: (prog_pos, double)}    default-coef table pairs (w at f, double at f+8)
      blob:   {objoff: bytes}                 global tables bulk-copied into the object
      tail:   [objoff...]                     coefRAM record-pointer fields (madd/umaddl tail)
      stride: coefRAM record size
    """
    c=ctor_addr(cls); s,e=lib.func(c)
    md=lib.md(); md.detail=True
    regs={}; wstore={}; xstore={}; blob={}; qsrc={}
    stride=None
    for i in md.disasm(lib.Z[s:e],s):
        m=i.mnemonic; t=(m+' '+i.op_str).strip()
        dst=_rd(i)
        if (mm:=re.match(rf'(?:mov|movz) (w\d+), #({HEX})$',t)):
            v=_num(mm.group(2))&0xffffffff; regs[mm.group(1)]=v; regs['x'+mm.group(1)[1:]]=v
        elif (mm:=re.match(rf'(?:mov|movz) (x\d+), #({HEX})$',t)):
            v=_num(mm.group(2))&0xffffffffffffffff; regs[mm.group(1)]=v; regs['w'+mm.group(1)[1:]]=v&0xffffffff
        elif (mm:=re.match(r'mov (x\d+), (xzr|x\d+)$',t)):
            v=0 if mm.group(2)=='xzr' else regs.get(mm.group(2))
            regs[mm.group(1)]=v; regs['w'+mm.group(1)[1:]]=None
        elif (mm:=re.match(r'mov (w\d+), (w\d+)$',t)):
            regs[mm.group(1)]=regs.get(mm.group(2)); regs['x'+mm.group(1)[1:]]=None
        elif (mm:=re.match(rf'movk (x\d+), #({HEX})(?:, lsl #(\d+))?$',t)):
            r=mm.group(1); sh=int(mm.group(3) or 0); base=regs.get(r)
            regs[r]=None if base is None else (base&~(0xffff<<sh))|(_num(mm.group(2))<<sh)
            regs['w'+r[1:]]=None
        elif (mm:=re.match(rf'adrp (x\d+), #({HEX})$',t)):
            regs[mm.group(1)]=_num(mm.group(2))
        elif (mm:=re.match(rf'(?:ldr|ldur) (q\d+|d\d+|s\d+), \[(x\d+)(?:, #({HEX}))?\]$',t)):
            b=regs.get(mm.group(2))
            qsrc[mm.group(1)]=None if b is None else b+_num(mm.group(3) or '0')
        elif (mm:=re.match(rf'stp (q\d+), (q\d+), \[x0, #({HEX})\]$',t)) or (mm:=re.match(r'stp (q\d+), (q\d+), \[x0\]$',t)):
            f=_num(mm.group(3)) if mm.lastindex and mm.lastindex>=3 else 0
            for j,g in enumerate((mm.group(1),mm.group(2))):
                v=qsrc.get(g)
                if v is not None: blob[f+16*j]=lib.Z[v:v+16]
        elif (mm:=re.match(rf'str (q\d+|d\d+), \[x0, #({HEX})\]$',t)):
            v=qsrc.get(mm.group(1)); n=16 if mm.group(1)[0]=='q' else 8
            if v is not None: blob[_num(mm.group(2))]=lib.Z[v:v+n]
        elif (mm:=re.match(rf'str (w\d+|wzr), \[x0(?:, #({HEX}))?\]$',t)):
            v=0 if mm.group(1)=='wzr' else regs.get(mm.group(1))
            wstore[_num(mm.group(2) or '0')]=v
        elif (mm:=re.match(rf'str (x\d+|xzr), \[x0(?:, #({HEX}))?\]$',t)):
            v=0 if mm.group(1)=='xzr' else regs.get(mm.group(1))
            xstore[_num(mm.group(2) or '0')]=v
        elif (mm:=re.match(r'(?:madd|umaddl) (x\d+), [wx]\d+, ([wx]\d+), x\d+$',t)):
            if stride is None: stride=regs.get(mm.group(2))
            regs[mm.group(1)]=None
        elif (mm:=re.match(rf'add (w\d+), (w\d+), #({HEX})$',t)):
            b=regs.get(mm.group(2)); regs[mm.group(1)]=None if b is None else b+_num(mm.group(3))
        if m=='bl':
            for r in list(regs):
                n=re.match(r'[wx](\d+)$',r)
                if n and int(n.group(1))<18: regs[r]=None
        elif dst and m not in('mov','movz','movk','adrp','ldr','ldur','stp','str','madd','umaddl','add','sub','ret','b'):
            regs[dst]=None
            if dst[0]=='x': regs['w'+dst[1:]]=None
            else: regs['x'+dst[1:]]=None
    coefs={}
    for f,v in sorted(wstore.items()):
        if v is not None and xstore.get(f+8) is not None:
            coefs[f]=(v, struct.unpack('<d',struct.pack('<Q',xstore[f+8]))[0])
    tail=sorted(f for f,v in xstore.items() if v is None)
    return dict(ctor=c,blob=blob,coefs=coefs,wstore=wstore,xstore=xstore,tail=tail,stride=stride)

def parse_datsym(cls, ct):
    """GetMemoryInSegmentWordAdrs -> (table_obj_base, count, [(syll_off, addr)])"""
    s,e,code=disasm_meth(cls,'GetMemoryInSegmentWordAdrs(_DataSym const*)')
    base=None; cnt=None
    for i in code:
        if i.mnemonic=='add' and i.op_str.startswith('x9, x9, #'): base=_num(i.op_str.split('#')[1])
        if i.mnemonic=='cmp' and i.op_str.startswith('x8, #'): cnt=_num(i.op_str.split('#')[1])
    blob=ct['blob']; recs=[]
    for k in range(cnt or 0):
        o=base+8*k
        cand=[b for b in blob if b<=o<b+len(blob[b])]
        recs.append(struct.unpack_from('<II',blob[cand[0]],o-cand[0]) if cand else (None,None))
    return base,cnt,recs
