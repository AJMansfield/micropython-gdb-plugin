import warnings
import gdb
import logging
from . import file
from . import mp
from . import qstr

log = logging.getLogger("mpgdb.obj")

obj_t = file.micropython.lookup_static_symbol('mp_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type
const_obj_t = file.micropython.lookup_static_symbol('mp_const_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type
rom_obj_t = file.micropython.lookup_static_symbol('mp_rom_obj_t', gdb.SYMBOL_TYPE_DOMAIN).type

def is_obj(o: gdb.Value) -> bool:
    return o.type.name in [obj_t.name, const_obj_t.name, rom_obj_t.name]

def decode_const_obj(o: gdb.Value) -> str|None:
    if is_obj(o):
        i = int(o)
        if i == mp.macro.MP_OBJ_NULL:
            return "null"
        if i == mp.macro.MP_OBJ_STOP_ITERATION:
            return "StopIteration"
        if i == mp.macro.MP_OBJ_SENTINEL:
            return "sentinel"
        if i == mp.macro.MP_ROM_NONE:
            return "None"
        if i == mp.macro.MP_ROM_FALSE:
            return "False"
        if i == mp.macro.MP_ROM_TRUE:
            return "True"

def decode_immediate_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and mp.macro_fn.MP_OBJ_IS_IMMEDIATE_OBJ(o):
        return mp.macro_fn.MP_OBJ_IMMEDIATE_OBJ_VALUE(o)

def decode_smallint_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and mp.macro_fn.MP_OBJ_IS_SMALL_INT(o):
        return mp.macro_fn.MP_OBJ_SMALL_INT_VALUE(o)
    
def decode_object_obj(o: gdb.Value) -> int|None:
    if is_obj(o) and mp.macro_fn.MP_OBJ_IS_OBJ(o):
        return mp.macro_fn.MP_OBJ_TO_PTR(o).cast(mp.obj.object)


class ObjConstPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return self.__value

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_const_obj(value)
            if decoded is not None:
                return cls(decoded)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e


class ObjImmediatePrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return f"imm({self.__value})"

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_immediate_obj(value)
            if decoded is not None:
                return cls(decoded)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

class ObjSmallIntPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        return self.__value

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_smallint_obj(value)
            if decoded is not None:
                return cls(decoded)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

class ObjObjPrinter(gdb.ValuePrinter):
    def __init__(self, value: gdb.Value):
        self.__value = value

    def to_string(self):
        try:
            return self.__value.address.format_string(raw=True)
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
        
    def children(self):
        try:
            for field in  self.__value.type.fields():
                yield (field.name, self.__value[field])
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

    @classmethod
    def lookup(cls, value: gdb.Value):
        try:
            decoded = decode_object_obj(value)
            if decoded is None:
                return None
                    
            for type_name in mp.type:
                type_obj = getattr(mp.type, type_name, None)
                if type_obj is None:
                    continue
                if type_obj != decoded["base"]["type"]:
                    continue
                    
                typedef = getattr(mp.obj, type_name, None)
                if typedef is None:
                    continue

                decoded = decoded.cast(typedef)
                
            return cls(decoded.dereference())
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

POSSIBLE_SLOTS = [
    "make_new",
    "print",
    "call",
    "unary_op",
    "binary_op",
    "attr",
    "subscr",
    "iter",
    "buffer",
    "protocol",
    "parent",
    "locals_dict",
]

class ObjBasePrinter(gdb.ValuePrinter):
    def __init__(self, value):
        self.__value = value

    def to_string(self):
        try:
            return qstr.lookup(self.__value['type']['name']).string()
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e
    
    def children(self):
        try:
            yield ("type", self.__value['type'])
            yield ("name", self.__value['type']['name'].cast(qstr.qstr_short_t))
            for slot in POSSIBLE_SLOTS:
                if mp.macro_fn.MP_OBJ_TYPE_HAS_SLOT(self.__value['type'], slot):
                    yield (slot, mp.macro_fn.MP_OBJ_TYPE_GET_SLOT(self.__value['type'], slot))
        except Exception as e:
            log.exception("%r", e, exc_info=True, stack_info=True)
            raise e

    @classmethod
    def lookup(cls, value):
        if value.type == mp.obj.base.target():
            return cls(value)
        else:
            return None
        
file.micropython.pretty_printers.append(ObjConstPrinter.lookup)
log.info("Registered pretty printer: %s", ObjConstPrinter.__name__)
file.micropython.pretty_printers.append(ObjImmediatePrinter.lookup)
log.info("Registered pretty printer: %s", ObjImmediatePrinter.__name__)
file.micropython.pretty_printers.append(ObjSmallIntPrinter.lookup)
log.info("Registered pretty printer: %s", ObjSmallIntPrinter.__name__)
file.micropython.pretty_printers.append(ObjObjPrinter.lookup)
log.info("Registered pretty printer: %s", ObjObjPrinter.__name__)
file.micropython.pretty_printers.append(ObjBasePrinter.lookup)
log.info("Registered pretty printer: %s", ObjBasePrinter.__name__)

# TODO specific object printers:
# str, vstr
# tuple, attrtuple, namedtuple, list, set

