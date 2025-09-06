import logging
log = logging.getLogger("mpgdb.commands")
import gdb
from . import depver

class CommandPrefix(gdb.Command):
    """Examine MicroPython interpreter state."""
    def __init__(self):
        super().__init__("mpy", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND, True)
        log.info("Registered command prefix: mpy")
command_prefix = CommandPrefix()


if depver.GDB >= "17.0":
    _ParameterPrefix = gdb.ParameterPrefix
else:
    class _ParameterPrefix:  # Directly copied from GDB 17.0
        class _PrefixCommand(gdb.Command):
            def __invoke(self, args, from_tty):
                class MarkActiveCallback:
                    def __init__(self, cmd, delegate):
                        self.__cmd = cmd
                        self.__delegate = delegate
                    def __enter__(self):
                        self.__delegate.active_prefix = self.__cmd
                    def __exit__(self, exception_type, exception_value, traceback):
                        self.__delegate.active_prefix = None
                assert callable(self.__cb)
                with MarkActiveCallback(self, self.__delegate):
                    self.__cb(args, from_tty)

            @staticmethod
            def __find_callback(delegate, mode):
                cb = getattr(delegate, "invoke_" + mode, None)
                if callable(cb):
                    return cb
                return None

            def __init__(self, mode, name, cmd_class, delegate, doc=None):
                assert mode == "set" or mode == "show"
                if doc is None:
                    self.__doc__ = delegate.__doc__
                else:
                    self.__doc__ = doc
                self.__cb = self.__find_callback(delegate, mode)
                self.__delegate = delegate
                if self.__cb is not None:
                    self.invoke = self.__invoke
                super().__init__(mode + " " + name, cmd_class, prefix=True)

        def __init__(self, name, cmd_class, doc=None):
            self.active_prefix = None
            self._set_prefix_cmd = self._PrefixCommand("set", name, cmd_class, self, doc)
            self._show_prefix_cmd = self._PrefixCommand("show", name, cmd_class, self, doc)


class ParameterPrefix(_ParameterPrefix):
    """Control MicroPython plugin settings."""
    def __init__(self):
        super().__init__("mpy", gdb.COMMAND_USER)
        log.info("Registered parameter prefix: mpy")
parameter_prefix = ParameterPrefix()