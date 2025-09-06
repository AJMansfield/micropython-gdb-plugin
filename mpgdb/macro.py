import warnings
import gdb

FLAG_NAMES = dict.fromkeys([
    'MICROPY_OBJ_REPR',
    'MICROPY_OBJ_REPR_A',
    'MICROPY_OBJ_REPR_B',
    'MICROPY_OBJ_REPR_C',
    'MICROPY_OBJ_REPR_D',
])

INTEGRAL_NAMES = dict.fromkeys([ # MP_{}
    'OBJ_NULL',
    'OBJ_STOP_ITERATION',
    'OBJ_SENTINEL',
    'ROM_NONE',
    'ROM_FALSE',
    'ROM_TRUE',

    'TYPE_FLAG_NONE',
    'TYPE_FLAG_IS_SUBCLASSED',
    'TYPE_FLAG_HAS_SPECIAL_ACCESSORS',
    'TYPE_FLAG_EQ_NOT_REFLEXIVE',
    'TYPE_FLAG_EQ_CHECKS_OTHER_TYPE',
    'TYPE_FLAG_EQ_HAS_NEQ_TEST',
    'TYPE_FLAG_BINDS_SELF',
    'TYPE_FLAG_BUILTIN_FUN',
    'TYPE_FLAG_ITER_IS_GETITER',
    'TYPE_FLAG_ITER_IS_ITERNEXT',
    'TYPE_FLAG_ITER_IS_CUSTOM',
    'TYPE_FLAG_ITER_IS_STREAM',
    'TYPE_FLAG_INSTANCE_TYPE',
    'TYPE_FLAG_SUBSCR_ALLOWS_STACK_SLICE',
    'TYPE_FLAG_IS_INSTANCED',
    'TYPE_FLAG_HAS_FINALISER',
])

def _lookup_integral(name: str) -> gdb.Type:
    fullname = "MP_{}".format(name)
    value = gdb.parse_and_eval(fullname, True)
    return int(value)

FUNCTION_NAMES = { # MP_{}
    'OBJ_FROM_PTR': "((mp_obj_t)({}))",
    'OBJ_TO_PTR': "((void *)({}))", 
    'OBJ_IS_SMALL_INT': "(((mp_int_t)({})) & 1) != 0",
    'OBJ_SMALL_INT_VALUE': "(((mp_int_t)({})) >> 1)",
    'OBJ_NEW_SMALL_INT': "((mp_obj_t)((((mp_uint_t)({})) << 1) | 1))",
    'OBJ_IS_QSTR': "(((mp_int_t)({})) & 7) == 2",
    'OBJ_QSTR_VALUE': "(((mp_uint_t)({})) >> 3)",
    'OBJ_NEW_QSTR': "((mp_obj_t)((((mp_uint_t)({})) << 3) | 2))", 
    'OBJ_IS_IMMEDIATE_OBJ': "(((mp_int_t)({})) & 7) == 6",
    'OBJ_IMMEDIATE_OBJ_VALUE': "(((mp_uint_t)({})) >> 3)",
    'OBJ_NEW_IMMEDIATE_OBJ': "((mp_obj_t)((({}) << 3) | 6))",
    'OBJ_IS_OBJ': "(((mp_int_t)({})) & 3) == 0",
    'OBJ_TYPE_HAS_SLOT': "(((mp_obj_type_t *){0})->slot_index_{1})",
    'OBJ_TYPE_GET_SLOT': "(_MP_OBJ_TYPE_SLOT_TYPE_{1}((mp_obj_type_t *){0})->slots[((mp_obj_type_t *){0})->slot_index_{1} - 1])",
}

def _format_raw(value):
    try:
        return value.format_string(raw=True, symbols=False, address=True, deref_refs=False)
    except AttributeError:
        return str(value)

def _lookup_function(name: str) -> gdb.Type:
    fullname = "MP_{}".format(name)
    def f(*args: gdb.Value):
        raw_args = list(_format_raw(a) for a in args)
        try:
            arglist = ",".join(raw_args)
            expr = f"{fullname}({arglist})"
            return gdb.parse_and_eval(expr, True)
        except gdb.error: # fallback REPR_A-only mode
            expr = FUNCTION_NAMES[name].format(*raw_args)
            return gdb.parse_and_eval(expr, True)
    f.__name__ = name
    return f

def __getattr__(name: str) -> gdb.Type:
    if name in FUNCTION_NAMES:
        return _lookup_function(name)
    
    if name in INTEGRAL_NAMES:
        symbol = INTEGRAL_NAMES.get(name, None)
        if symbol is not None:
            return symbol
        
        symbol = _lookup_integral(name)
        if symbol is not None:
            INTEGRAL_NAMES[name] = symbol
            return symbol
        
        if name in INTEGRAL_NAMES:
            del INTEGRAL_NAMES[name]

        raise AttributeError(f"Can't find MP_{name}.", name=name)

    
def __dir__() -> list[str]:
    return list(INTEGRAL_NAMES)
