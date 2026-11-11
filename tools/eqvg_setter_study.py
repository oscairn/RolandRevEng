"""Record original EqVGenv/EqVG setter calls against an owned manager fixture."""
from contextlib import contextmanager,ExitStack
import struct

from eqvg_study import report,checked_args,native_function,native_interpolation_function,update_plan
from eqfa_study import _adr
from line_shaping_study import _finite


@contextmanager
def native_function_setter(output=False):
    """The manager only records; no event loop, interpolation worker or device runs."""
    import ctypes
    import lib
    from native_callback_fixture import executable_mapping
    if type(output)is not bool:raise ValueError('Expected explicit output-stage boolean')
    report();start,end=(0x354184,0x354490)if output else(0x19b8ec,0x19bbd4)
    md=lib.md();md.detail=True;code=list(md.disasm(lib.Z[start:end],start))
    if [i.address for i in code]!=list(range(start,end,4)):raise ValueError('Incomplete setter body')
    with ExitStack()as stack:
        generate=stack.enter_context(native_function());stable=stack.enter_context(native_interpolation_function())
        blob=bytearray(lib.Z[start:end]);blob.extend(bytes(-len(blob)%8));targets={}
        for target,pointer in ((0x20d8f4,generate.address),(0x20defc,stable.address)):
            targets[target]=len(blob);blob.extend(struct.pack('<IIQ',0x58000050,0xd61f0200,pointer))
        guard=len(blob);blob.extend(struct.pack('<Q',0x3141592653589793))
        trap=len(blob);blob.extend(struct.pack('<II',0xd4200000,0xd65f03c0))
        for ins in code:
            offset=ins.address-start
            if ins.mnemonic=='bl':
                target=ins.operands[0].imm
                if target not in (*targets,0x6d8710):raise ValueError('Unexpected setter direct dependency')
                destination=targets[target]if target in targets else trap
                blob[offset:offset+4]=struct.pack('<I',0x94000000|(((destination-offset)//4)&0x3ffffff))
            elif ins.mnemonic=='adrp':
                if not output or ins.operands[1].imm!=0x9c8000:raise ValueError('Unexpected setter global')
                register=int(ins.op_str.split(',')[0][1:])
                if code[(offset//4)+1].op_str!=f'x{register}, [x{register}, #0x480]':
                    raise ValueError('Unexpected stack guard access')
                blob[offset:offset+8]=_adr(register,guard-offset)+bytes.fromhex('1f2003d5')
            elif (ins.mnemonic=='b'or ins.mnemonic.startswith('b.'))and not start<=ins.operands[0].imm<end:
                raise ValueError('Setter branch leaves owned body')
        address=stack.enter_context(executable_mapping(bytes(blob)))
        invoke=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_bool,
            ctypes.c_double,ctypes.c_double,ctypes.c_double)(address)
        def record(kind,cutoff,gain=0.,q=1.,*,current=(0.,-1.),envelope=True,subtract_one=True):
            checked_args(kind,cutoff,gain,q,44100)
            if type(envelope)is not bool or type(subtract_one)is not bool:
                raise ValueError('Expected explicit envelope/offset booleans')
            if not isinstance(current,(list,tuple))or len(current)!=2:raise ValueError('Expected current stored a/b')
            current=tuple(map(_finite,current));calls=[];errors=[]
            table=ctypes.create_string_buffer(0x1a0);manager=ctypes.create_string_buffer(8)
            descriptor=ctypes.create_string_buffer(0x30);piece=ctypes.create_string_buffer(0x18)
            struct.pack_into('<B',descriptor,0,int(subtract_one))
            for i in range(5):struct.pack_into('<Q',descriptor,8+8*i,i+1)
            struct.pack_into('<Q',manager,0,ctypes.addressof(table))
            struct.pack_into('<QQI',piece,0,ctypes.addressof(manager),ctypes.addressof(descriptor),7)
            callbacks=[]
            def read(_,symbol,*index):
                if symbol not in (1,2):errors.append('Unexpected coefficient read');return 0.
                if index and index!=(7,):errors.append('Unexpected piece index')
                return current[symbol-1]
            def write(slot):
                def capture(_,symbol,*args):
                    index=args[0]if slot in (0x178,0x188)else None
                    if index is not None and index!=7:errors.append('Unexpected piece index')
                    if not 1<=symbol<=5:errors.append('Unexpected coefficient symbol')
                    value=args[-1];selector=args[1]if slot==0x178 else None
                    wait=bool(args[2])if slot==0x178 else False
                    calls.append(dict(coefficient=symbol-1,value=value,manager_slot=slot,
                        time_selector=selector,wait=wait))
                return capture
            def batch(_,symbols,values,count,selector):
                if count not in (1,4,5)or selector!=100:
                    errors.append('Unexpected literal interpolation batch');return
                calls.append(dict(manager_slot=0xf8,coefficients=list(symbols[:count]),
                    values=list(values[:count]),count=count,time_selector=selector))
            signatures=((0x198,ctypes.c_double,(ctypes.c_void_p,ctypes.c_int),read),
                (0xe0,ctypes.c_double,(ctypes.c_void_p,),read),
                (0x178,None,(ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_bool,ctypes.c_double),write(0x178)),
                (0x188,None,(ctypes.c_void_p,ctypes.c_int,ctypes.c_double),write(0x188)),
                (0xc8,None,(ctypes.c_void_p,ctypes.c_double),write(0xc8)),
                (0xf8,None,(ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_double),ctypes.c_int,ctypes.c_int),batch))
            for slot,restype,arguments,callback in signatures:
                function=ctypes.CFUNCTYPE(restype,ctypes.c_void_p,*arguments)(callback);callbacks.append(function)
                struct.pack_into('<Q',table,slot,ctypes.cast(function,ctypes.c_void_p).value)
            invoke(ctypes.addressof(piece),kind,envelope,cutoff,gain,q)
            if errors:raise ValueError('; '.join(errors))
            return calls
        yield record
