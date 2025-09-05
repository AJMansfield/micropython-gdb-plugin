

class MpyMapPrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value
        
    def children(self):
        try:
            obj = self.__value
            yield ("all_keys_are_qstrs", obj['all_keys_are_qstrs'])
            yield ("is_fixed", obj['is_fixed'])
            yield ("is_ordered", obj['is_ordered'])
            yield ("used", obj['used'])
            yield ("alloc", obj['alloc'])
            yield ("table", obj.cast(gdb.lookup_type("mp_map_debug_t")))
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    @classmethod
    def lookup(cls, value):
        if str(value.type) in {"mp_map_t"}:
            return cls(value)
        else:
            return None
gdb.current_objfile().pretty_printers.append(MpyMapPrinter.lookup)
log.info("Registered pretty printer: %s", MpyMapPrinter.__name__)


class MpyMapTablePrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value
    
    def to_string(self):
        try:
            obj = self.__value.cast(gdb.lookup_type("mp_map_t"))
            return obj['table']
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def children(self):
        try:
            obj = self.__value.cast(gdb.lookup_type("mp_map_t"))
            n = 0
            for i in range(obj['alloc']):
                if mp_map_slot_is_filled(obj, i):
                    elem = obj['table'][i]
                    # yield(f"[{elem['key']}]", elem['value'])
                    # yield(f"[{str(elem['key'])}]", elem['value'])
                    yield (f"[{n}]", elem['key'])
                    yield (f"[{n+1}]", elem['value'])
                    n += 2
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def display_hint(self):
        return 'map'
    
    @classmethod
    def lookup(cls, value):
        if str(value.type) in {"mp_map_debug_t"}:
            return cls(value)
        else:
            return None
gdb.current_objfile().pretty_printers.append(MpyMapTablePrinter.lookup)
log.info("Registered pretty printer: %s", MpyMapTablePrinter.__name__)