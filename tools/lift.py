# Lift SIM_*::VSubProc into an ordered op list with resolved operands.
#
# Facts relied on (validated in validate.py against all 5 programs):
#  - obj+0...: default-coefficient table {u32 prog_pos, double value} stride 0x10 (ctor constants).
#      VSubProc `ldr d,[x8,#F]` with F = entry+8 reads that default value.
#  - obj+K...: data-sym table stride 8 {u32 syll_off, u32 addr}; GetMemoryInSegmentWordAdrs
#      returns &rec+4, so object field K+8i+4 contains `addr`. VSubProc `ldr w,[x8,#K+8i+4]`
#      loads it; syll_off = byte offset of the big-endian 16-bit address syllable in the program
#      (top nibble = memory-space tag: 0=data mem, 2=IO, 4=coeff-RAM window).
#  - obj+T...: coefficient-RAM record pointers (ctor madd tail; record size 0x48).
#      VSubProc reads the live value at [ptr+0x28].
#  - memory-base register: value from segment-array field +0x18 = data memory (index &0x7ff),
#      +0x28 = IO/window memory (unmasked index).
import struct, re, sys
import lib, parse

def helpers():
    a2n={}
    for n,a in lib.load_exports().items(): a2n.setdefault(a,n)
    return a2n

def known_fields(cls):
    ln,A,B,tab,b0,b1=parse.program(cls)
    ct=parse.parse_ctor(cls)
    dbase,dcnt,drecs=parse.parse_datsym(cls,ct)
    f2rec={dbase+8*i+4:(a,v) for i,(a,v) in enumerate(drecs)}
    f2coef={f+8:(p,d) for f,(p,d) in ct['coefs'].items()}
    tail=ct['tail']
    f2slot={f:i for i,f in enumerate(tail)}
    return ln,A,B,tab,ct,dbase,drecs,f2rec,f2coef,f2slot,tail

TAG={0:'DM',2:'IO',4:'CF',6:'C6',0xc:'C8',8:'C0?',1:'D1',3:'I3'}
HEX=r'-?(?:0x)?[0-9a-fA-F]+'
def _num(s): return int(s,16) if s.startswith(('0x','-0x')) else int(s)

def lift(cls):
    ln,A,B,tab,ct,dbase,drecs,f2rec,f2coef,f2slot,tail=known_fields(cls)
    a2n=helpers()
    s,e,code=parse.disasm_meth(cls,'VSubProc(double const**, double**)')
    ops=[]
    def sylinfo(a):
        w=struct.unpack_from('>H',A,a)[0]
        return w
    addrpend={}    # w-reg -> resolved address record
    slotreg={}     # x-reg -> coef-RAM slot index
    regtag={}      # reg -> 'grpA'(seg-group) | 'grpB'(io-group) | 'DM' | 'IO' | 'in' | 'out'
    for i in code:
        m=i.mnemonic; o=i.op_str; t=(m+' '+o).strip(); pc=i.address
        if m=='ldr' and (mm:=re.match(rf'(w\d+), \[x\d+, #({HEX})\]$',o)):
            f=_num(mm.group(2)); r=mm.group(1)
            if f>=dbase+4 and f in f2rec and f2rec[f][0] is not None:
                a,v=f2rec[f]; w=sylinfo(a)
                addrpend[r]=(f,a,w)
                ops.append((pc,'load-addr-const',r,
                    'obj+%#x -> syl@%#x=%04x space=%s eff=%#x'%(f,a,w,TAG.get(w>>12,hex(w>>12)),w&0xfff)))
            else:
                nm={0x10:'sample-counter',0x20:'counter2',0x24:'counter3'}.get(f,'obj+%#x'%f)
                addrpend[r]=None
                ops.append((pc,'load-counter',r,nm))
            continue
        if m=='ldr' and (mm:=re.match(r'(x\d+), \[x\d+, #0x(10|28)\]$',o)):
            regtag[mm.group(1)]='grpA' if mm.group(2)=='10' else 'grpB'
            continue
        if m=='ldr' and (mm:=re.match(r'(x\d+), \[(x\d+), #0x(18|28)\]$',o)):
            par=regtag.get(mm.group(2))
            regtag[mm.group(1)]='DM' if (mm.group(3)=='18' and par in('grpA',None)) or par=='DM' else 'IO'
            ops.append((pc,'load-membase',mm.group(1),regtag[mm.group(1)]+' segment array'))
            continue
        if m=='ldr' and (mm:=re.match(rf'(x\d+), \[x\d+, #({HEX})\]$',o)):
            f=_num(mm.group(2)); r=mm.group(1)
            if f in f2slot:
                slotreg[r]=f2slot[f]
                ops.append((pc,'load-coefptr',r,'obj+%#x -> coef-RAM slot %d'%(f,f2slot[f])))
            elif f in (0x18,0x28,0x30):
                pass  # engine plumbing pointer loads
            else:
                ops.append((pc,'load-ptr',r,'obj+%#x'%f))
            continue
        if m=='ldr' and (mm:=re.match(rf'(d\d+), \[x\d+, #({HEX})\]$',o)):
            f=_num(mm.group(2)); c=f2coef.get(f)
            ops.append((pc,'coef-default' if c else 'load-dbl-field',mm.group(1),
                 ('prog@%s default %.9g'%(hex(c[0]),c[1])) if c else 'obj+%#x'%f))
            continue
        if m=='ldr' and (mm:=re.match(rf'(s\d+), \[(x\d+), #0x28\]$',o)):
            sl=slotreg.get(mm.group(2))
            ops.append((pc,'coef-RAM-read',mm.group(1),
                        'slot %d live value'%sl if sl is not None else 'via %s (?)'%mm.group(2)))
            continue
        if m=='ldr' and (mm:=re.match(r'(x\d+), \[(x\d+), #0x(18|28)\]$',o)):
            regtag[mm.group(1)]='DM' if mm.group(3)=='18' else 'IO'
            continue
        if m in('ldr','str') and (mm:=re.match(rf'(d\d+), \[(x\d+), (?:w(\d+), uxtw #3|x(\d+))\]$',o)):
            wr='w'+(mm.group(3) or mm.group(4))
            sp=regtag.get(mm.group(2),'?')
            ap=addrpend.get(wr)
            if ap:
                f,a,w=ap
                ops.append((pc,m+'-'+sp+'-mem',mm.group(1),
                    'syl@%#x=%04x space=%s eff=%#x'%(a,w,TAG.get(w>>12,hex(w>>12)),w&0xfff)))
            else:
                ops.append((pc,m+'-'+sp+'-mem',mm.group(1),'dyn via w%s'%wr))
            continue
        if m=='and' and ('#0x7ff' in o):
            d_,s1,_=[x.strip() for x in o.split(',')]
            if addrpend.get(s1) is not None: addrpend[d_]=addrpend[s1]
            ops.append((pc,'addr-wrap-2048',o,'')); continue
        if m=='and' and ('#0x3fffff' in o): ops.append((pc,'addr-wrap-4M',o,'')); continue
        if m in('fmul','fnmul','fadd','fsub','fmadd','fmsub','fneg','fdiv','fmin','fmax','fmaxnm','fminnm','fsqrt'):
            ops.append((pc,'alu-'+m,o,'')); continue
        if m in('fcmp','fcsel','fccmp','cset','cmp','orr'):
            ops.append((pc,'cmp/sel',t,'')); continue
        if m in('fcvt','fcvtzs','scvtf','ucvtf','fmov','movi'):
            ops.append((pc,'conv/mov',t,'')); continue
        if m=='bl':
            tgt=_num(o.lstrip('#'))
            ops.append((pc,'call',hex(tgt),a2n.get(tgt,'extern'))); continue
        if m in('b','b.le','b.gt','b.eq','b.ne','b.ge','b.lt'):
            ops.append((pc,'branch',t,'')); continue
        if m in('add','sub') and re.match(rf'[wx]\d+, [wx]\d+, ({HEX}|[wx]\d+)$',o):
            d_,s1,s2=[x.strip() for x in o.split(',')]
            p1=addrpend.get(s1); p2=addrpend.get(s2)
            if p1 is not None and s1[0]=='w': addrpend[d_]=p1
            elif p2 is not None and s2[0]=='w': addrpend[d_]=p2
            else: addrpend[d_]=None
            ops.append((pc,'int-'+m,o,'')); continue
        if m in('stp','ldp','ret','sub','add','mov'): continue
        ops.append((pc,'other',t,''))
    return ops,ln,A,B,tab

if __name__=='__main__':
    cls=sys.argv[1]
    ops=lift(cls)[0]
    for o in ops: print('%x %-16s %-22s %s'%(o[0],o[1],o[2],o[3]))
