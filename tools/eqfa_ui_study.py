"""FDRV EqFa UI indices/scaling and an owned VUpdatePrm dispatch fixture."""
from contextlib import contextmanager
import hashlib
import struct

from line_shaping_study import NATIVE_SHA256,_float32

START,END=0x352f60,0x3535b0
TYPE_MAP=(0,6,7,3,4)
GROUPS=(('input',(0,1),0x20,2),('resample',(4,5,6),0x30,0),
        ('post0',(8,9,10),0x40,0),('post1',(11,12,13),0x40,1))
FIELDS={v for _,indices,_,_ in GROUPS for v in indices}


def events(values,changed,frame=0):
    if (not isinstance(values,dict)or not isinstance(changed,(list,tuple,set))
            or type(frame)is not int or frame<0):raise ValueError('Expected UI snapshot, changed indices and frame')
    if (any(type(k)is not int or k not in FIELDS or type(v)is not int or not -(1<<31)<=v<(1<<31)
            for k,v in values.items())or any(type(k)is not int or k not in FIELDS for k in changed)):
        raise ValueError('Unsupported UI index/value outside the checked EqFa fields')
    result=[]
    for stage,indices,_,_ in GROUPS:
        if not set(indices)&set(changed):continue
        if any(k not in values for k in indices):raise ValueError('Changed group requires its complete UI snapshot')
        if stage=='input':kind=3;cutoff,gain=(values[k]for k in indices)
        else:
            index,cutoff,gain=(values[k]for k in indices)
            if not 0<=index<len(TYPE_MAP):raise ValueError('UI filter selector outside recovered five-entry table')
            kind=TYPE_MAP[index]
        result.append(dict(frame=frame,stage=stage,type=kind,cutoff=float(cutoff),
            gain=_float32(_float32(gain)/10.)))
    return result


def report():
    import lib
    from weighted_mix_study import require_instructions
    if hashlib.sha256(lib.Z).hexdigest()!=NATIVE_SHA256:raise ValueError('Expected pinned native image')
    raw=lib.Z[0x83d014:0x83d028]
    if struct.unpack('<5i',raw)!=TYPE_MAP or not lib.Z[0x83d028:].startswith(b'11CMfxFDRVPrm\0'):
        raise ValueError('UI type table or its adjacent symbol boundary changed')
    code=list(lib.md().disasm(lib.Z[START:END],START));instructions={i.address:i for i in code}
    if len(code)*4!=END-START or any(i.mnemonic=='bl'for i in code):raise ValueError('Unexpected UI direct call')
    for slot,address in ((0x20,0xe7418),(0x30,0xe7610),(0x40,0xe7790)):
        if struct.unpack_from('<Q',lib.Z,0x9e3240+slot)[0]!=address:raise ValueError('FDRV virtual setter slot changed')
    for pc in (0x352fdc,0x35317c,0x3532c4,0x353380):
        require_instructions(instructions,pc,(('scvtf','s0, w0'),('fmov','s1, #10.00000000'),
            ('fdiv','s0, s0, s1'),('fcvt','d1, s0')))
    require_instructions(instructions,0x352ffc,(('mov','w1, #2'),('mov','w2, #3')))
    return dict(native_sha256=NATIVE_SHA256,function=[START,END],ui_type_map=TYPE_MAP,
        type_table=0x83d014,type_table_sha256=hashlib.sha256(raw).hexdigest(),
        groups=[dict(stage=s,indices=i,setter_slot=slot,selector=selector)for s,i,slot,selector in GROUPS],
        frequency_conversion='signed integer to binary64 directly; frequency units inferred from EqFaCal cutoff/rate',
        gain_conversion='signed integer to binary32, binary32 divide by10, then promote to binary64',
        changed_input='explicit logical changed-index set; no raw flag-word protocol inferred',
        global_ui_ranges_proved=False,hardware_execution_verified=False)


@contextmanager
def native_function():
    import ctypes
    import lib
    from eqfa_study import _adr
    from native_callback_fixture import executable_mapping
    report();blob=bytearray(lib.Z[START:END]);blob.extend(bytes(-len(blob)%8))
    table=len(blob);blob.extend(lib.Z[0x83d000:0x83d028])
    md=lib.md();md.detail=True
    for ins in md.disasm(lib.Z[START:END],START):
        if ins.mnemonic=='adrp':
            if ins.operands[1].imm!=0x83d000:raise ValueError('Unexpected UI global data access')
            register=int(ins.op_str.split(',')[0][1:]);offset=ins.address-START
            blob[offset:offset+4]=_adr(register,table-offset)
    with executable_mapping(bytes(blob))as address:
        invoke=ctypes.CFUNCTYPE(None,ctypes.c_void_p)(address)
        def calculate(values,changed,frame=0):
            expected=events(values,changed,frame);result=[];errors=[]
            getter_table=ctypes.create_string_buffer(0x20);getter=ctypes.create_string_buffer(8)
            setter_table=ctypes.create_string_buffer(0x58);setter=ctypes.create_string_buffer(8)
            parent=ctypes.create_string_buffer(0x90)
            def get(_,index):
                if index not in values:errors.append(f'Unexpected value read {index}')
                return values.get(index,0)
            get_cb=ctypes.CFUNCTYPE(ctypes.c_int32,ctypes.c_void_p,ctypes.c_int32)(get)
            changed_cb=ctypes.CFUNCTYPE(ctypes.c_uint8,ctypes.c_void_p,ctypes.c_int32)(lambda _,i:int(i in changed))
            unexpected=ctypes.CFUNCTYPE(None,ctypes.c_void_p)(lambda _:errors.append('Unexpected setter'))
            callbacks=[get_cb,changed_cb,unexpected]
            for offset,callback in ((0x10,get_cb),(0x18,changed_cb)):
                struct.pack_into('<Q',getter_table,offset,ctypes.cast(callback,ctypes.c_void_p).value)
            for offset in range(0,0x58,8):struct.pack_into('<Q',setter_table,offset,ctypes.cast(unexpected,ctypes.c_void_p).value)
            def recorder(method):
                def record(_,selector,kind,cutoff,gain,unused):
                    if method=='input':stage='input';valid=selector==2
                    elif method=='resample':stage='resample';valid=selector==0
                    else:stage='post0'if selector==0 else'post1';valid=selector in (0,1)
                    if not valid or unused!=0.:errors.append('Unexpected setter selector/third parameter')
                    result.append(dict(frame=frame,stage=stage,type=kind,cutoff=cutoff,gain=gain))
                return record
            for slot,method in ((0x20,'input'),(0x30,'resample'),(0x40,'post')):
                callback=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,
                    ctypes.c_double,ctypes.c_double,ctypes.c_double)(recorder(method));callbacks.append(callback)
                struct.pack_into('<Q',setter_table,slot,ctypes.cast(callback,ctypes.c_void_p).value)
            for buffer,offset,target in ((getter,0,getter_table),(setter,0,setter_table),
                (parent,8,getter),(parent,0x88,setter)):
                struct.pack_into('<Q',buffer,offset,ctypes.addressof(target))
            invoke(ctypes.addressof(parent))
            if errors:raise ValueError('; '.join(errors))
            if result!=expected:raise ValueError(f'Native UI dispatch differs: {result} != {expected}')
            return result
        yield calculate


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-native',action='store_true')
    args=parser.parse_args();result=report()
    if args.execute_native:
        snapshot={0:200,1:17,4:1,5:4000,6:-31,8:3,9:600,10:63,11:2,12:90,13:0}
        with native_function()as native:result['native_events']=native(snapshot,FIELDS)
    print(json.dumps(result,indent=2))
