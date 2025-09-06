import gdb
import logging
from . import file
from . import macro

log = logging.getLogger("mpgdb.map")

void = gdb.lookup_type("void")

map_typedef = file.micropython.lookup_static_symbol("mp_map_t", gdb.SYMBOL_TYPE_DOMAIN).type
map_elem = file.micropython.lookup_static_symbol("mp_map_elem_t",  gdb.SYMBOL_TYPE_DOMAIN).type
# map_elem = file.micropython.lookup_static_symbol("mp_map_elem_t",  gdb.SYMBOL_TYPE_DOMAIN).type
map_elem_dcp = map_elem.pointer().const().pointer().const()

def slot_is_filled(map: gdb.Value, pos: int):
    return int(map['table'][pos]['key']) not in { macro.OBJ_NULL, macro.OBJ_SENTINEL }

class MapPrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value: gdb.Value = value
        
    def children(self):
        try:
            obj = self.__value
            # yield ("&", obj.address.cast(void.pointer()))
            yield ("all_keys_are_qstrs", obj['all_keys_are_qstrs'])
            yield ("is_fixed", obj['is_fixed'])
            yield ("is_ordered", obj['is_ordered'])
            yield ("used", obj['used'])
            yield ("alloc", obj['alloc'])
            yield ("table", obj['table'].const_value().address.const_value())
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    @classmethod
    def lookup(cls, value: gdb.Value):
        if value.type == map_typedef:
            return cls(value)

class TablePrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value
    
    def to_string(self):
        try:
            return self.__value['table']
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def children(self):
        try:
            obj = self.__value
            n = 0
            for i in range(obj['alloc']):
                elem = obj['table'][i]
                if slot_is_filled(obj, i):
                    elem = obj['table'][i]
                    yield (f"[{n}]", elem['key'])
                    yield (f"[{n+1}]", elem['value'])
                    n += 2
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def display_hint(self):
        return 'map'
    
    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            if value.type == map_elem_dcp:
                value = value.cast(void.pointer())
                value -= map_typedef['table'].bitpos//8
                value = value.cast(map_typedef.pointer())
                return cls(value.dereference())
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e


file.micropython.pretty_printers.append(MapPrinter.lookup)
log.info("Registered pretty printer: %s", MapPrinter.__name__)

file.micropython.pretty_printers.append(TablePrinter.lookup)
log.info("Registered pretty printer: %s", TablePrinter.__name__)