# emulate a SIM_*::<coef table init> function: collect {u32 rel, double val} pairs stored at [x0+off]
import capstone,struct,sys
def coeftab(Z,start,end):
    md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM); md.detail=True
    regs={}; mem={}
    for i in md.disasm(Z[start:end],start):
        m=i.mnemonic; ops=i.operands
        if m in('mov','movz') and ops[1].type==capstone.arm64.ARM64_OP_IMM:
            regs[i.reg_name(ops[0].reg)[1:]]=ops[1].imm&0xffffffffffffffff
        elif m=='mov' and ops[1].type==capstone.arm64.ARM64_OP_REG:
            src=i.reg_name(ops[1].reg)
            if src in('xzr','wzr'): regs[i.reg_name(ops[0].reg)[1:]]=0
            elif src[1:] in regs: regs[i.reg_name(ops[0].reg)[1:]]=regs[src[1:]]
        elif m=='movk':
            r=i.reg_name(ops[0].reg)[1:]; sh=ops[1].shift.value if ops[1].shift.type else 0
            regs[r]=(regs.get(r,0)&~(0xffff<<sh))|(ops[1].imm<<sh)
        elif m=='str' and i.reg_name(ops[1].mem.base)=='x0':
            src=i.reg_name(ops[0].reg)
            v=0 if src in('xzr','wzr') else regs.get(src[1:])
            mem[ops[1].mem.disp]=(src[0],v)
        elif m in('ret','b','bl','br'): break
    out=[]
    for off in sorted(mem):
        k,v=mem[off]
        if k=='w' and off+8 in mem and mem[off+8][0]=='x':
            d=struct.unpack('<d',struct.pack('<Q',mem[off+8][1] or 0))[0]
            out.append((v,d,mem[off+8][1]))
    return out
if __name__=='__main__':
    Z=open(sys.argv[1],'rb').read()
    for rel,d,raw in coeftab(Z,int(sys.argv[2],16),int(sys.argv[3],16)): print(hex(rel),d,hex(raw or 0))
