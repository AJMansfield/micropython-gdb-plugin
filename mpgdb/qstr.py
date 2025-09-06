import gdb
import logging
from . import file
from . import obj
from . import macro

log = logging.getLogger("mpgdb.qstr")

qstr_t = file.micropython.lookup_static_symbol("qstr", gdb.SYMBOL_TYPE_DOMAIN).type
qstr_short_t = file.micropython.lookup_static_symbol("qstr_short_t", gdb.SYMBOL_TYPE_DOMAIN).type

saved = None

def decode_qstr(o: gdb.Value) -> int|None:
    if obj.is_obj(o) and macro.OBJ_IS_QSTR(o):
        return macro.OBJ_QSTR_VALUE(o)
    elif o.type.name in [qstr_t.name, qstr_short_t.name]:
        return o

def lookup(qstr: int) -> gdb.Value|None:
    pool = file.micropython.lookup_global_symbol("mp_state_ctx", domain=gdb.SYMBOL_VAR_DOMAIN).value()["vm"]["last_pool"]

    qstr_max = int(pool["total_prev_len"]) + int(pool["len"])
    if(qstr >= qstr_max):
        return None
    
    while(qstr < int(pool["total_prev_len"])):
        pool = pool["prev"]
    
    return pool["qstrs"][qstr - int(pool["total_prev_len"])]

def get(qstr: int|gdb.Value) -> gdb.Value|None:
    qstr = decode_qstr(qstr)
    if qstr is not None:
        return lookup(qstr)
    

class QstrPrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value
    
    def to_string(self):
        try:
            return lookup(self.__value).string()
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    def children(self):
        try:
            yield (f"qstr[{int(self.__value)}]", lookup(self.__value))
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    def display_hint(self):
        return 'string'
    
    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_qstr(value)
            if decoded is not None:
                return cls(decoded)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
file.micropython.pretty_printers.append(QstrPrinter.lookup)
log.info("Registered pretty printer: %s", QstrPrinter.__name__)