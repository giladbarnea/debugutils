__version__ = '0.1.0'
print(f'{__name__ = }')
print(f'{__file__ = }')
import inspect as inspect_
from contextlib import suppress
import os
try:
    builtins = __import__("__builtin__")
except ImportError:
    builtins = __import__("builtins")


with suppress(ModuleNotFoundError):
    from IPython import start_ipython
    
    
    def startipy():
        frame_info = _get_caller_frame_info(offset=1)
        start_ipython(argv=[], user_ns={**frame_info.frame.f_locals, **globals()})
    
    
    builtins.startipy = startipy

with suppress(ModuleNotFoundError):
    from icecream import ic
    
    builtins.ic = ic

import rich
# from rich.pretty import install
# install(console=con,indent_guides=True,expand_all=True)

def mm(topic, subtopic=None):
    mm_args = f'{topic}'
    if subtopic:
        mm_args += f' {subtopic}'
    import subprocess as sp
    sp.check_call(f'-m manuals {mm_args}', executable='/home/gilad/dev/manuals/env/bin/python')
