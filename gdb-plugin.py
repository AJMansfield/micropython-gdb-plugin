import logging, sys, os, importlib
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("gdb.micropython")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    sys.path.append('/usr/share/gdb/python/')
    import gdb

try:
    if TYPE_CHECKING:
        import mpy_tool
    else:
        if "mpy-tool" not in sys.modules:
            mpy_tools_folder = os.path.normpath(os.path.join(gdb.current_objfile().filename, "..", "..", "..", "..", "tools"))
            log.info("Importing mpy-tool from %s.", mpy_tools_folder)

            sys.modules["makeqstrdata"]={}
            sys.path.append(mpy_tools_folder)
            mpy_tool = importlib.import_module("mpy-tool")
        mpy_tool = sys.modules["mpy-tool"]
    log.info("Imported mpy-tool.")
    has_mpy_tool = True
except ImportError:
    log.warning("Cannot import mpy-tool. Disassembly will be unavailable.")
    has_mpy_tool = False

class MPy(gdb.Command):
    """Examine MicroPython interpreter state."""
    def __init__(self):
        super(MPy, self).__init__("mpy", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND, True)
        log.info("Registered group: mpy")
MPy()


def get_qstr(qstr: int) -> str:
    last_pool = gdb.lookup_symbol("mp_state_ctx")[0].value()["vm"]["last_pool"]
    while(qstr < int(last_pool["total_prev_len"])):
        last_pool = last_pool["prev"]
    return last_pool["qstrs"][qstr - int(last_pool["total_prev_len"])].string()

class Qstr(gdb.Command):
    """Decode a uniQueSTR value.
    Usage: mpy qstr VALUE
    """
    def __init__(self):
        super(Qstr, self).__init__("mpy qstr", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)
        log.info("Registered command: mpy qstr")
    
    def invoke(self, args, from_tty):
        print(get_qstr(int(args)))
Qstr()


def get_pystate(frame):
    try:
        return frame.read_var("code_state")
    except ValueError:
        return get_pystate(frame.older())
    except AttributeError:
        return None
        
class PyState(gdb.Command):
    """Show the MicroPython stack.
    Usage: mpy state
    """
    def __init__(self):
        super(PyState, self).__init__("mpy state", gdb.COMMAND_STACK, gdb.COMPLETE_NONE)
        log.info("Registered command: mpy state")
    
    def invoke(self, args, from_tty):
        frame = gdb.selected_frame()
        code_state = get_pystate(frame)
        n_state = int(code_state["n_state"])
        state = code_state["state"]
        for i in range(n_state):
            print(get_pyobj(state[i]))
PyState()


def get_pyobj(value):
    if int(value) & 1:
        return str(int(value) >> 1)
    if (int(value) & 7) == 2:
        return "'" + get_qstr(int(value) >> 3) + "'"
    if int(value) == 0:
        return "None"
    objtype = value.cast(mp_base_obj)["type"]
    if int(objtype) == int(mp_type_dict):
        dic = value.cast(mp_obj_dict)
        vals = int(dic["map"]["alloc"])
        strs = ""
        for i in range(vals):
            entry = dic["map"]["table"][i]
            strs += get_pyobj(entry["key"]) + ": " + get_pyobj(entry["value"]) + ",\n "
        return "dict: {" + strs + "}"
    if int(objtype) == int(mp_type_module) and False:
        print("module")
        dic = value.cast(mp_obj_module)
        print(dic)
        return "module(" + get_pyobj(dic["globals"]) + ")"
    obj = str(objtype).split(" ")
    if len(obj) == 1:
        obj = obj[0]
    else:
        obj = obj[1]
    return "object(" + hex(value) + ") " + obj

class PyObj(gdb.Command):
    """Pretty-print a MicroPython object.
    Usage: mpy obj VALUE
    """
    def __init__(self):
        super(PyObj, self).__init__("mpy obj", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)
        log.info("Registered command: mpy obj")

    def complete(self, text, word):
        return gdb.COMPLETE_NONE

    def invoke(self, args, from_tty):
        print(get_pyobj(gdb.parse_and_eval(args)))
PyObj()


def get_pydis(bc):
    sig = MPY_BC_Sig()
    sig.load(bc, 0)
    sig.print()
    mpy_disassemble(bc, sig.end, None)

class PyDis(gdb.Command):
    """Dissasemble MicroPython bytecode.
    Usage: mpy dis VALUE
    """
    def __init__(self):
        super(PyDis, self).__init__("mpy dis", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION)
        log.info("Registered command: mpy dis")

    def invoke(self, args, from_tty):
        value = gdb.parse_and_eval(args)
        objtype = value.cast(mp_base_obj)["type"]
        if int(objtype) == int(mp_type_fun_bc):
            get_pydis(value.cast(mp_obj_fun_bc))

if has_mpy_tool:
    PyDis()


def mpy_disassemble(fun_bc, ptr, current_ptr):
    Opcode = mpy_tool.Opcode

    bc = fun_bc["bytecode"]
    qstr_table = fun_bc["context"]["constants"]["qstr_table"]
    obj_table = fun_bc["context"]["constants"]["obj_table"]
    biggest_jump = 0
    instructions = []
    offsets = []
    labels = dict()
    ip = ptr
    while True:
        offsets.append(ptr)
        op = int(bc[ip])
        fmt, sz, arg, _ = mpy_tool.mp_opcode_decode(bc, ip)
        if (bc[ip] & 0xf0) == Opcode.MP_BC_BASE_JUMP_E:
            biggest_jump = max(biggest_jump, ip + arg)
        if bc[ip] == Opcode.MP_BC_LOAD_CONST_OBJ:
            arg = get_pyobj(obj_table[arg])
            pass
        if fmt == mpy_tool.MP_BC_FORMAT_QSTR:
            arg = get_qstr(int(qstr_table[arg]))
        elif fmt in (mpy_tool.MP_BC_FORMAT_VAR_UINT, mpy_tool.MP_BC_FORMAT_OFFSET):
            pass
        else:
            arg = ""
        print(
            "  %04x %s %s" % (ip - ptr, Opcode.mapping[bc[ip]], arg)
        )
        if bc[ip] == Opcode.MP_BC_RETURN_VALUE:
            if biggest_jump < ip:
                break
        ip += sz
        #self.disassemble_children()

# bytecode layout:
#
#  func signature  : var uint
#      contains six values interleaved bit-wise as: xSSSSEAA [xFSSKAED repeated]
#          x = extension           another byte follows
#          S = n_state - 1         number of entries in Python value stack
#          E = n_exc_stack         number of entries in exception stack
#          F = scope_flags         four bits of flags, MP_SCOPE_FLAG_xxx
#          A = n_pos_args          number of arguments this function takes
#          K = n_kwonly_args       number of keyword-only arguments this function takes
#          D = n_def_pos_args      number of default positional arguments
#
#  prelude size    : var uint
#      contains two values interleaved bit-wise as: xIIIIIIC repeated
#          x = extension           another byte follows
#          I = n_info              number of bytes in source info section (always > 0)
#          C = n_cells             number of bytes/cells in closure section
#
#  source info section:
#      simple_name : var qstr      always exists
#      argname0    : var qstr
#      ...         : var qstr
#      argnameN    : var qstr      N = num_pos_args + num_kwonly_args - 1
#      <line number info>
#
#  closure section:
#      local_num0  : byte
#      ...         : byte
#      local_numN  : byte          N = n_cells-1
#
#  <bytecode>                   // bytecode layout:
class MPY_BC_Sig:
    def __init__(self):
        pass

    def load(self, fun_bc, ip):
        bytecode = fun_bc["bytecode"]
        qstr_table = fun_bc["context"]["constants"]["qstr_table"]
        sig = mpy_tool.extract_prelude(bytecode, ip)
        (self.S, self.E, self.F, self.A, self.K, self.D) = sig[5]
        (self.I, self.C) = sig[6]
        self.end = sig[4]
        self.lines = []
        print(qstr_table[0])
        self.function_name = Qstr.get_qstr(int(qstr_table[sig[7][0]]))
        self.args = [get_qstr(qstr_table[int(i)]) for i in sig[7][1:]]
        self.source = get_qstr(qstr_table[0])
            
        #now 1 qstr function name
        #now A + K strings, args
        source_line = 1
        ptr = sig[2]
        while ptr < sig[3]:
            c = int(bytecode[ptr])
            b = 0
            l = 0
            if (c & 0x80) == 0:
                # 0b0LLBBBBB encoding
                b = c & 0x1f
                l = c >> 5
                ptr += 1
            else:
                # 0b1LLLBBBB 0bLLLLLLLL encoding (l's LSB in second byte)
                b = c & 0xf
                l = ((c << 4) & 0x700) | int(bytecode[ptr + 1])
                ptr += 2
            self.lines.append((l,b))

    def set_val(self, S, E, F, A, K, D, C, I):
        self.S = S
        self.E = E
        self.F = F
        self.A = A
        self.K = K
        self.D = D
        self.C = C
        self.I = I

    def map_line(self, ip):
        line = 1
        for (l, b) in self.lines:
            if b > ip:
                break
            line += l
            ip -= b
        return line

    def print(self):
        print("state: " + str(self.S) + ", exc: " + str(self.E) + ", scope: " + str(self.F) + ", pos_args: " + str(self.A) + ", kwonly_args: " + str(self.K) + ", def_args: " + str(self.D) + ", info: " + str(self.I) + ", cells: " + str(self.C))

mp_base_obj = gdb.lookup_type("mp_obj_base_t").pointer()
mp_obj_dict = gdb.lookup_type("mp_obj_dict_t").pointer()
mp_type_dict = gdb.lookup_symbol("mp_type_dict")[0].value().address
mp_obj_module = gdb.lookup_type("mp_obj_module_t").pointer()
mp_type_module = gdb.lookup_symbol("mp_type_module")[0].value().address
mp_obj_fun_bc = gdb.lookup_type("mp_obj_fun_bc_t").pointer()
mp_type_fun_bc = gdb.lookup_symbol("mp_type_fun_bc")[0].value().address


    
class InlinedFrameDecorator(gdb.FrameDecorator.FrameDecorator):

    def __init__(self, fobj):
        super(InlinedFrameDecorator, self).__init__(fobj)
        self.elided_frames = []
        frame = self.inferior_frame()
        self.sig = MPY_BC_Sig()
        self.sig.load(frame.read_var("code_state")["fun_bc"], 0)

    def function(self):
        frame = self.inferior_frame()
        state = frame.read_var("code_state")["state"]
        name = self.sig.function_name
        narg = 0
        if len(self.sig.args) != 0:
            name += "("
            for arg in self.sig.args:
                name += arg + "=" + str(get_pyobj(state[self.sig.S - 1 - narg])) + ","
                narg += 1
            name = name[:-1]+")"
        return name


    #def elided(self):
    #    return self.elided_frames

    def filename(self):
        return self.sig.source

    def line(self):
        frame = self.inferior_frame()
        ip = int(frame.read_var("code_state")["ip"]) - int(frame.read_var("code_state")["fun_bc"]["bytecode"][0].address)
        return self.sig.map_line(ip)

def decorate(frames):
    try:
        while True:
            frame = next(frames)
            if frame.inferior_frame().name() == "mp_execute_bytecode":
                out = InlinedFrameDecorator(frame)
                frame = next(frames)
                if frame.inferior_frame().name() == "fun_bc_call":
                    out.elided_frames.append(frame)
                    frame = next(frames)
                    if frame.inferior_frame().name() == "mp_call_function_n_kw":
                        out.elided_frames.append(frame)
                        frame = None
                yield out
                if frame is not None:
                    yield frame
            else:
                yield frame
    except StopIteration:
        pass
    
class FrameFilter():
    def __init__(self):
        self.name = "mpy_frame"
        self.priority = 100
        self.enabled = True

        # Register this frame filter with the global frame_filters
        # dictionary.
        gdb.frame_filters[self.name] = self
        
        log.info("Registered frame filter: %s", self.name)

    def filter(self, frame_iter):
        return iter(decorate(frame_iter))
    
if has_mpy_tool:
    FrameFilter()

log.info("Loaded MicroPython GDB Plugin")