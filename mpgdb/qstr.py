import gdb
from . import file

# qstr_t = file.micropython.lookup_static_symbol("qstr", gdb.SYMBOL_TYPE_DOMAIN)
# qstr_short_t = file.micropython.lookup_static_symbol("qstr_short_t", gdb.SYMBOL_TYPE_DOMAIN)

def convert_obj_to_qstr(o: gdb.Value) -> int|None:
    if (int(o) & 7) == 2:  # only valid for REPR_A
        return int(o) >> 3
    else:
        return None
    # return gdb.parse_and_eval(f"MP_OBJ_QSTR_VALUE({int(o)})")

def get(qstr: int|gdb.Value) -> gdb.Value|None:
    if isinstance(qstr, gdb.Value):
        if qstr.type.strip_typedefs().code == gdb.TYPE_CODE_PTR:  # assume it's an mp_obj_t, try to decode it
            qstr = convert_obj_to_qstr(qstr)
        if qstr is None:
            return None
        qstr = int(qstr)
    
    pool = file.micropython.lookup_global_symbol("mp_state_ctx", domain=gdb.SYMBOL_VAR_DOMAIN).value()["vm"]["last_pool"]

    qstr_max = int(pool["total_prev_len"]) + int(pool["len"])
    if(qstr >= qstr_max):
        return None
    
    while(qstr < int(pool["total_prev_len"])):
        pool = pool["prev"]
    
    return pool["qstrs"][qstr - int(pool["total_prev_len"])]
