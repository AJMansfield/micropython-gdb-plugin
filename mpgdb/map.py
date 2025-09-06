import gdb
import logging
from . import file
from . import mp

log = logging.getLogger("mpgdb.map")

void = gdb.lookup_type("void")

map_typedef = file.micropython.lookup_static_symbol("mp_map_t", gdb.SYMBOL_TYPE_DOMAIN).type
map_elem = file.micropython.lookup_static_symbol("mp_map_elem_t",  gdb.SYMBOL_TYPE_DOMAIN).type
# map_elem = file.micropython.lookup_static_symbol("mp_map_elem_t",  gdb.SYMBOL_TYPE_DOMAIN).type
map_elem_dcp = map_elem.pointer().const().pointer().const()

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
            array_type = map_elem.vector(obj['alloc'] - 1).pointer()
            yield ("table", obj['table'].cast(array_type))
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    @classmethod
    def lookup(cls, value: gdb.Value):
        if value.type == map_typedef:
            return cls(value)

class MapTablePrinter(gdb.ValuePrinter):
    class EntriesParameter(gdb.Parameter):
        """Configure which mp_map_entry_t slots to show.
        filled = Show only filled map slots.
        all = Show all slots, including [sentinel] and [null].
        """
        FILLED = "filled"
        ALL = "all"
        ENUM = [FILLED, ALL]
        def __init__ (self, name:str):
            self.set_doc = "Configure which mp_map_entry_t slots to show."
            super().__init__(name, gdb.COMMAND_DATA, gdb.PARAM_ENUM, self.ENUM)
            log.info("Registered parameter: %s", name)

        def should_show(self, entry:gdb.Value):
            if self.value == self.FILLED:
                return entry['key'] not in [ mp.macro.MP_OBJ_NULL, mp.macro.MP_OBJ_SENTINEL ]
            elif self.value == self.ALL:
                return True
            
    entries = EntriesParameter("mpy map_entries")

    def __init__(self, value: gdb.Value):
        self.__value = value
    
    def to_string(self):
        try:
            return self.__value.address.cast(void.pointer())
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def children(self):
        try:
            obj = self.__value
            size = obj.type.sizeof // obj.type.target().sizeof

            for i in range(size):
                elem = obj[i]
                if self.entries.should_show(elem):
                    yield (f"[{i}].key", elem['key'])
                    yield (f"[{i}].value", elem['value'])
            
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def display_hint(self):
        return 'map'
    
    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            if value.type.code == gdb.TYPE_CODE_PTR:
                try:
                    value = value.dereference()
                except gdb.error: # (void *) -> Attempt to dereference a generic pointer.
                    return
            if value.type.code == gdb.TYPE_CODE_ARRAY:
                elem = value.type.target().unqualified()
                if elem == map_elem:
                    return cls(value)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

file.micropython.pretty_printers.append(MapPrinter.lookup)
log.info("Registered pretty printer: %s", MapPrinter.__name__)

file.micropython.pretty_printers.append(MapTablePrinter.lookup)
log.info("Registered pretty printer: %s", MapTablePrinter.__name__)