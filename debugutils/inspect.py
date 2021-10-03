"""
exec(compile(open("/home/gilad/debug.py").read(), "/home/gilad/debug.py", 'exec'))
exec(compile((Path.home() / Path('debug.py')).open().read(), "/home/gilad/debug.py", 'exec'))
exec(compile(Path(debug := os.getenv("PYTHONDEBUGFILE", Path(os.getenv("HOME")) / 'debug.py')).open().read(), debug, 'exec'))
# %run '/home/gilad/debug.py'

# DEBUGFILE_FORCE_INSTALL, DEBUGFILE_RICH_TB, DEBUGFILE_PATCH_PRINT, DEBUGFILE_PATCH_LOGGING, DEBUGFILE_LOADED
"""

import os

# os.getenv('DEBUGFILE_LOADED')
import sys
from typing import Union, Tuple, List, NoReturn, Literal
from contextlib import suppress

__force_install = os.getenv('DEBUGFILE_FORCE_INSTALL', '')

try:
    builtins = __import__("__builtin__")
except ImportError:
    builtins = __import__("builtins")

try:
    import rich
except ModuleNotFoundError:
    if 'rich' in __force_install:
        # DEBUGFILE_FORCE_INSTALL='rich icecream'
        os.system(f'pip install {__force_install}')
    raise

import inspect as inspect_
import re
from rich.console import Console


# TODO: instead of patching builtins, get namespace (print this file's locals when called from IPython etc)
def __build_getprops_getmeths():
    Constraint = Literal['regular', 'private', 'dunder']
    
    def __build_constraints(only: Union[Constraint, Tuple[Constraint]]):
        """If `only` is None, this means no constraints: `regular = private = dunder = True` (show all).
        If it's a string (e.g. 'regular'), switch on `regular = True`, and switch off others (show only regular props).
        If it's a tuple (e.g. `('regular', 'private')`), switch on `regular = True, private = True` (don't show dunder)."""
        
        def __build_constraint(_constraint: Constraint, _regular: bool, _private: bool, _dunder: bool) -> Tuple[bool, bool, bool]:
            if _constraint == 'regular':
                _regular = True
            elif _constraint == 'private':
                _private = True
            elif _constraint == 'dunder':
                _dunder = True
            else:
                con.log("[WARN] 'only' arg is can be only (an iterable composed of) 'regular', 'private' or 'dunder'. returning as-is")
            return _regular, _private, _dunder
        
        if only is not None:
            regular = private = dunder = False
            if isinstance(only, str):
                regular, private, dunder = __build_constraint(only, regular, private, dunder)
            else:  # iterable
                for constraint in only:
                    regular, private, dunder = __build_constraint(constraint, regular, private, dunder)
        else:
            regular = private = dunder = True
        return regular, private, dunder
    
    def __ismeth(value) -> bool:
        string = str(type(value))
        return 'method' in string or 'wrapper' in string or 'function' in string
    
    def __should_skip(prop, regular: bool, private: bool, dunder: bool, *, include, exclude) -> bool:
        if prop in exclude:
            return True
        if include and prop not in include:
            return True
        if prop.startswith('__'):
            if not dunder:
                return True
        elif prop.startswith('_'):
            if not private:
                return True
        elif not regular:
            return True
        return False
    
    def _getprops(obj,
                  values: bool = False,
                  only: Union[Constraint, Tuple[Constraint]] = None,
                  exclude: Union[str, Tuple] = (),
                  include: Union[str, Tuple] = ()
                  ):
        """
        :param values: Specify True to check and return property values
        :param only: Either 'regular', 'private', 'dunder' or a tuple containing any of them
        :param exclude: A str or a tuple of strings specifying which props to ignore.
        :param include: A str or a tuple of strings specifying which props to include. All others are ignored.
        `exclude` and `include` are mutually exclusive.
        """
        # TODO: compare rv with inspect.getmembers()
        if include and exclude:
            con.log(f"[WARN] _getprops({repr(obj)}) | can't have both include and exclude")
            return
        if include:
            # ensure include is a tuple
            if isinstance(include, str):
                include = (include,)
        if exclude:
            # ensure exclude is a tuple
            if isinstance(exclude, str):
                exclude = (exclude,)
        try:
            proplist = obj.__dir__()
        except:
            proplist = dir(obj)
        props = []
        regular, private, dunder = __build_constraints(only)
        __obj_props = ('__class__', '__doc__')
        for prop in proplist:
            if __should_skip(prop, regular, private, dunder, include=include, exclude=(*exclude, *__obj_props), ):
                continue
            try:
                value = getattr(obj, prop)
            except Exception as e:
                con.log(f'{e.__class__.__qualname__} when trying to get attr: "{prop}": {", ".join(map(repr, e.args))}. skipping.')
                continue
            if __ismeth(value):
                continue
            if values:
                props.append({prop: value})
            else:
                props.append(prop)
        if values:
            sort = lambda x: next(iter(x))
        else:
            sort = None
        return sorted(props, key=sort)
    
    def _getmeths(obj,
                  sigs: bool = False,
                  only: Union[Constraint, Tuple[Constraint]] = None,
                  exclude: Union[str, Tuple] = (),
                  include: Union[str, Tuple] = ()) -> List[str]:
        """
        :param sigs: Specify True to check and return method signatures
        :param only: Either 'regular', 'private', 'dunder' or a tuple containing any of them
        :param exclude: A str or a tuple of strings specifying which props to ignore.
        :param include: A str or a tuple of strings specifying which props to include. All others are ignored.
        `exclude` and `include` are mutually exclusive.
        """
        if include and exclude:
            con.log(f"[WARN] _getprops({repr(obj)}) | can't have both include and exclude")
            return []
        if include:
            # ensure include is a tuple
            if isinstance(include, str):
                include = (include,)
        if exclude:
            # ensure exclude is a tuple
            if isinstance(exclude, str):
                exclude = (exclude,)
        try:
            proplist = obj.__dir__()
        except:
            proplist = dir(obj)
        regular, private, dunder = __build_constraints(only)
        meths = []
        __obj_meths = ('__delattr__',
                       '__dir__',
                       '__eq__',
                       '__format__',
                       '__ge__',
                       '__getattribute__',
                       '__gt__',
                       '__hash__',
                       '__init__',
                       '__init_subclass__',
                       '__le__',
                       '__lt__',
                       '__ne__',
                       '__new__',
                       '__reduce__',
                       '__reduce_ex__',
                       '__repr__',
                       '__setattr__',
                       '__sizeof__',
                       '__str__',
                       '__subclasshook__')
        for prop in proplist:
            if __should_skip(prop, regular, private, dunder, include=include, exclude=(*exclude, *__obj_meths), ):
                continue
            try:
                meth = getattr(obj, prop)
            except Exception as e:
                con.log(f'[_getmeths({obj})] {e.__class__.__qualname__} when trying to get attr: "{prop}": {", ".join(map(repr, e.args))}. skipping.')
                continue
            if not __ismeth(meth):
                continue
            if sigs:
                try:
                    sig: inspect_.Signature = inspect_.signature(meth)
                    meths.append({f'{prop}()': dict(sig.parameters.items())})
                except ValueError as e:
                    con.log(f'[_getmeths({obj})] ValueError: {", ".join(map(repr, e.args))}. appending meth without args')
                    meths.append(prop)
            else:
                meths.append(prop)
        if sigs:
            sort = lambda x: next(iter(x))
        else:
            sort = None
        return sorted(meths, key=sort)
    
    def _inspectfn(fn: callable) -> NoReturn:
        """Calls all relevant functions from `inspect` module on `fn` and prints the results.
        Doesn't return anything."""
        for inspectmethname in filter(lambda m: str(m)
                                                not in ('getsource', 'getsourcelines', 'findsource', 'getmembers'),
                                      _getmeths(inspect_)):
            if inspectmethname.startswith('is'):
                continue
            try:
                inspectmeth = getattr(inspect_, inspectmethname)
                rv = inspectmeth(fn)
                con.print(f'\n[b bright_white]{inspectmeth.__name__}({fn.__name__})[/] → {type(rv).__qualname__}:', end='\n    ')
                con.print(rv, end='\n')
            except Exception as e:
                con.log(f'[_inspectfn({fn})] {e.__class__.__qualname__}: {", ".join(map(repr, e.args))}')
    
    return _getprops, _getmeths, _inspectfn


getprops, getmeths, inspectfn = __build_getprops_getmeths()
con = Console(log_time_format='[%d.%m.%Y][%T]', file=sys.stderr)



def _get_caller_frame_info(offset=2) -> inspect_.FrameInfo:
    currframe = inspect_.currentframe()
    outer = inspect_.getouterframes(currframe)
    frameinfo = outer[offset]
    return frameinfo


def _get_var_info(arg_idx=0,
                  offset_or_frameinfo: Union[int, inspect_.FrameInfo] = 2,
                  *,
                  with_filename=True,
                  with_fnname=True) -> str:
    try:
        if isinstance(offset_or_frameinfo, int):
            frameinfo = _get_caller_frame_info(offset_or_frameinfo + 1)
        else:
            frameinfo = offset_or_frameinfo
        ctx = frameinfo.code_context[0].strip()
        output = ''
        if with_filename:
            output += f'{frameinfo.filename.split("/")[-1]} | '
        if with_fnname:
            output += f'{frameinfo.function}() | '
        
        argnames = ctx[ctx.find('(') + 1:-1].split(', ')
        if arg_idx is None:
            output += ', '.join(map(str.strip, argnames))
        else:
            output += argnames[arg_idx].strip()
        return output
    except Exception as e:
        con.log(f'_get_var_info({arg_idx = !r}, {offset_or_frameinfo = !r}, {with_filename = }, {with_fnname = })', e.__class__.__qualname__, e)
        return ""


def what(obj, **kwargs):
    """rich.inspect(methods=True)"""
    rich.inspect(obj, methods=True, title=_get_var_info(), **kwargs)


def ww(obj, **kwargs):
    """rich.inspect(methods=True, help=True)"""
    rich.inspect(obj, methods=True, help=True, title=_get_var_info(), **kwargs)


def www(obj, **kwargs):
    """rich.inspect(methods=True, help=True, private=True)"""
    rich.inspect(obj, methods=True, help=True, private=True, title=_get_var_info(), **kwargs)


def wwww(obj, **kwargs):
    """rich.inspect(all=True)"""
    rich.inspect(obj, all=True, title=_get_var_info(), **kwargs)


def who():
    con.log('locals:', log_locals=True, _stack_offset=2)


# builtins_before = set(builtins.__dict__.keys())
builtins.sys = sys
builtins.rich = rich
builtins.inspect = inspect_
builtins._get_var_info = _get_var_info
builtins._get_caller_frame_info = _get_caller_frame_info
builtins.getprops = getprops
builtins.getmeths = getmeths
builtins.inspectfn = inspectfn
builtins.mm = mm
builtins.what = what
builtins.ww = ww
builtins.www = www
builtins.wwww = wwww
builtins.who = who
builtins.pr = rich.print
builtins.con = con


if os.getenv('DEBUGFILE_RICH_TB') or any(arg == '--rich-tb' for arg in sys.argv[1:]):
    from rich.traceback import install
    
    install(extra_lines=5, show_locals=True)

if os.getenv('DEBUGFILE_PATCH_PRINT', '').lower() in ('1', 'true', 'yes') or any(arg == '--patch-print' for arg in sys.argv[1:]):
    from pprint import pformat as _pformat
    
    termwidth = os.get_terminal_size()[0] or 120
    pformat = lambda x: _pformat(x, indent=2, width=termwidth)
    # from rich.pretty import pretty_repr as rich_pretty_repr
    # builtins.pretty_repr = pretty_repr
    OBJ_RE = re.compile(r'<(?:[\w\d<>]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')
    TYPE_RE = re.compile(r"<class '(?:[\w\d<>]+\.)*([\w\d]+)'>")  # why not just just type.__name__?
    
    
    def pretty_repr(obj) -> str:
        if isinstance(obj, dict):
            return pformat(obj)
        if isinstance(obj, str):
            representation = obj
        else:
            representation = pformat(obj)
        if representation.startswith('<class'):
            return pretty_type(representation)
        return pretty_obj(representation)
    
    
    def pretty_obj(obj) -> str:
        if isinstance(obj, str):
            string = obj
        else:
            string = str(obj)
        return OBJ_RE.sub(lambda match: f'{(groups := match.groups())[0]} ({groups[1]})', string)
    
    
    def pretty_type(obj) -> str:
        stringified_type: str
        if isinstance(obj, str):
            # pretty_type(str(type(foo))
            stringified_type = obj
        elif type(obj) is type:
            # pretty_type(type(foo))
            stringified_type = str(obj)
        else:
            # pretty_type(foo)
            stringified_type = str(type(obj))
        return TYPE_RE.sub(lambda match: match.groups()[0], stringified_type)
    
    
    def print_patch(*args, **kwargs):
        """Keyword args support `offset = 2`, `with_filename = True`, `with_fnname = True`"""
        formatted_args = []
        caller_frameinfo = _get_caller_frame_info(offset=kwargs.pop('offset', 2))
        with_filename = kwargs.pop('with_filename', True)
        with_fnname = kwargs.pop('with_fnname', True)
        for i, arg in enumerate(args):
            var_info = _get_var_info(i,
                                     offset_or_frameinfo=caller_frameinfo,
                                     with_filename=not i and with_filename,
                                     with_fnname=not i and with_fnname)
            formatted_args.append(f'[bright_white]{var_info}:[/] [dim i]{pretty_type(arg)}[/]')
            # try:
            # pretty = pretty_repr(arg, max_width=160, expand_all=True)
            # except RecursionError:
            # 	from pprint import pformat
            # 	pretty = pformat(arg, indent=4, width=160, sort_dicts=True)
            pretty = pretty_repr(arg)
            
            formatted_args.append(pretty + '\n')
        rich.print(*formatted_args, **kwargs)
    
    
    # from copy import deepcopy
    
    # Todo: verify if patched
    # builtins.__print__ = deepcopy(print)
    builtins.pr = print_patch
    builtins.pretty_repr = pretty_repr
    builtins.pretty_obj = pretty_obj
    builtins.pretty_type = pretty_type
    builtins.OBJ_RE = OBJ_RE
    builtins.TYPE_RE = TYPE_RE

if os.getenv('DEBUGFILE_PATCH_LOGGING') or any(arg == '--patch-logging' for arg in sys.argv[1:]):
    import logging
    
    try:
        import loguru
    except ModuleNotFoundError:
        pass
    else:
        loggercls = logging.getLoggerClass()
        loggercls.debug = loguru.logger.debug
        loggercls.info = loguru.logger.info
        loggercls.warning = loguru.logger.warning
        loggercls.error = loguru.logger.error
        loggercls.exception = loguru.logger.exception

os.environ['DEBUGFILE_LOADED'] = '1'
