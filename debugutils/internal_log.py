import functools
import inspect
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

from loguru import logger as loguru_logger

loguru_logger.level("title", no=25, color='<bold><white>')


def title(self, msg):
    self.log("title", msg)


loguru_logger.__class__.title = title

try:
    raise ModuleNotFoundError
    from pygments.formatters import TerminalTrueColorFormatter
    from pygments.lexers import PythonLexer
    from pygments import highlight
    
    python_lexer = PythonLexer()
    monokai_formatter = TerminalTrueColorFormatter(style="monokai")
    
    native_formatter = TerminalTrueColorFormatter(style="native")
    
    
    def syntax_highlight(record):
        record["message"] = highlight(record["message"], python_lexer, monokai_formatter)
        fmt = '[<level>{level}</level>]\n{message}\n'
        return fmt
    
    
    class Formatter(logging.Formatter):
        def formatMessage(self, record: logging.LogRecord) -> str:
            if (record.levelno <= 10 or record.levelno >= 40) and len(record.message) < 10000:
                record.message = highlight(record.message, python_lexer, native_formatter)
            return super().formatMessage(record)


except ModuleNotFoundError:
    def syntax_highlight(record):
        fmt = '[<level>{level}</level>]\n{message}\n'
        return fmt
    
    
    from logging import Formatter

loguru_logger.configure(handlers=[
    dict(sink=sys.stderr, format=syntax_highlight)
    ])

old_factory = logging.getLogRecordFactory()

OBJ_RE = re.compile(r'<(?:[\w\d<>]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')
TYPE_RE = re.compile(r"<class '(?:[\w\d<>]+\.)*([\w\d]+)'>")
WHITESPACE_RE = re.compile(r'\s+')
COLOR_RE = re.compile(r'(\x1b\[(?:\d;?)*m)')

try:
    # from rich.pretty import pretty_repr as _pformat
    from rich.console import Console
    
    con = Console()
except ModuleNotFoundError:
    pass

from pprint import pformat as _pformat

termwidth = os.get_terminal_size()[0] or 120
pformat = lambda x: _pformat(x, indent=2, width=termwidth)


def pretty_signature_old(fn, fn_args, fn_kwargs):
    args = inspect.getfullargspec(fn)
    arg_names = args.args
    if args.defaults:
        arg_defaults = dict(zip(arg_names[-len(args.defaults):], args.defaults))
    else:
        arg_defaults = dict()
    pretty_sig = ", ".join([f'{k}={pretty_repr(v)}' for k, v in zip(arg_names, fn_args)])
    if len(arg_names) < len(fn_args):
        pretty_sig += ', ' + ', '.join(map(pretty_repr, fn_args[-len(arg_names):]))
    remaining_arg_names = arg_names[len(fn_args):]
    fn_kwargs_copy = dict(fn_kwargs)
    for a in remaining_arg_names:
        if a in fn_kwargs_copy:
            pretty_sig += f', {a}={pretty_repr(fn_kwargs_copy[a])}'
            del fn_kwargs_copy[a]
        elif a in arg_defaults:
            pretty_sig += f', {a}={pretty_repr(arg_defaults[a])}'
    if fn_kwargs_copy:
        for k, v in fn_kwargs_copy.items():
            pretty_sig += f', {k}={pretty_repr(v)}'
    return pretty_sig


def decolor(s):
    return COLOR_RE.sub('', s)


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
        stringified_type = obj
    elif type(obj) is type:
        stringified_type = str(obj)
    else:
        stringified_type = str(type(obj))
    return TYPE_RE.sub(lambda match: match.groups()[0], stringified_type)


def pretty_signature(method, *args, **kwargs) -> str:
    pretty_sig = "\033[97;48;2;30;30;30m"
    method_name = method.__name__ + "\033[0m"
    first_arg, *rest = args
    if hasattr(first_arg, method_name):
        args = rest
        if type(first_arg) is type:
            instance_name = first_arg.__qualname__
        else:
            instance_name = first_arg.__class__.__qualname__
        pretty_sig += f'{instance_name}.'
    args_pretty = ", ".join(map(pretty_repr, args)) if args else ''
    kwargs_pretty = ", ".join([f'{k}={pretty_repr(v)}' for k, v in kwargs.items()]) if kwargs else ''
    pretty_sig += f'{method_name}(' + args_pretty + (', ' if args and kwargs else '') + kwargs_pretty + ')'
    return pretty_sig


def shorten(s, limit=27):
    if not s:
        return s
    if limit < 4:
        logging.warning(f"shorten({shorten(repr(s), limit=20)}) was called with limit = %d, can handle limit >= 4", limit)
        return s
    length = len(s)
    if length > limit:
        half_the_limit = limit // 2
        try:
            escape_seq_start_index = s.index('\033[0m')
            no_color = decolor(s)
            real_length = len(no_color)
            if real_length <= limit:
                return s
            breakpoint()
            escape_seq_start_rindex = s.rindex('\033')
            left_cutoff = max(escape_seq_start_index + 4, half_the_limit)
            right_cutoff = min((real_length - escape_seq_start_rindex) + 4, half_the_limit)
            print(f'{limit = } | {length = } | {real_length = } | {left_cutoff = } | {right_cutoff = } | {half_the_limit = } | {escape_seq_start_index = } | {escape_seq_start_rindex = }')
        except ValueError:
            left_cutoff = max(half_the_limit - 3, 1)
            right_cutoff = max(half_the_limit - 4, 1)
            print(f'{limit = } | {length = } | {left_cutoff = } | {right_cutoff = } | {half_the_limit = }')
        free_chars = limit - left_cutoff - right_cutoff
        assert free_chars > 0, f'{free_chars = } not > 0'
        beginning = s[:left_cutoff]
        end = s[-right_cutoff:]
        if free_chars >= 7:
            separator = ' [...] '
        elif free_chars >= 5:
            separator = '[...]'
        elif free_chars >= 4:
            separator = ' .. '
        else:
            separator = '.' * free_chars
        assert len(separator) <= free_chars, f'{len(separator) = } ! <= {free_chars = }'
        return re.sub(r'\s+', ' ', f'{beginning}{separator}{end}')
    
    return s


def loginout(fn):
    identifier = fn.__qualname__
    
    @functools.wraps(fn)
    def decorator(*fn_args, **fn_kwargs):
        pretty_sig = pretty_signature_old(fn, fn_args, fn_kwargs)
        if not pretty_sig:
            pretty_sig = 'no args'
        _logger = loguru_logger.opt(depth=1)
        _logger.info(f'ENTERING: {identifier}({pretty_sig})...')
        retval = loguru_logger.catch()(fn(*fn_args, **fn_kwargs))
        _logger.info(f'RETURNING: {identifier}({shorten(pretty_sig)}) → {pretty_repr(retval)}')
        return retval
    
    return decorator


def log_method_calls(maybe_class=None, *, only=(), exclude=()):
    """
     A class decorator.
     Logs a message when a method of the decorated class is called (e.g `Calling: Calculator.add(1, 2)`),
     and another message before it returns (e.g `Calculator.add(1, 2) Returning → 3`).

     Examples:
         @log_method_calls
         class Calculator:
             def add(self, a, b): return a+b

         @log_method_call(only=['add'])
         class ProCalculator:
             def add(self, a, b): return a + b
             def divide(self, a, b): return a / b

     Args:
         only: Optional specify `only=['some_method', 'other_method']` to skip other methods.
         exclude: Optionally specify `exclude=['dont_care']` to skip specific methods.
     """
    cyan = lambda s: f'\033[2;3;36m{s}\033[0m'
    
    def decorator(cls_or_fn):
        if inspect.isfunction(cls_or_fn):
            def wrap(_method):
                def inner(*args, **kwargs):
                    pretty_sig = pretty_signature(_method, None, *args, **kwargs)
                    print('\n' + cyan('Calling: ') + f'{pretty_sig}\n')
                    rv = _method(*args, **kwargs)
                    print(f'\t {shorten(pretty_sig)} ' + cyan('Returning:\n\t → ') + pretty_repr(rv) + '\n')
                    return rv
                
                return inner
            
            return wrap(cls_or_fn)
        
        else:
            if only:
                condition = lambda x: x in only
            elif exclude:
                condition = lambda x: x not in exclude
            else:
                condition = lambda x: True
            methods = {v: attr for v, attr in vars(cls_or_fn).items() if inspect.isfunction(attr) and condition(v)}
            
            def wrap(_method):
                def inner(self, *args, **kwargs):
                    pretty_sig = pretty_signature(_method, self, *args, **kwargs)
                    print('\n' + cyan('Calling: ') + f'{pretty_sig}\n')
                    rv = _method(self, *args, **kwargs)
                    print(f'\t {shorten(pretty_sig)} ' + cyan('Returning:\n\t → ') + pretty_repr(rv) + '\n')
                    return rv
                
                return inner
            
            for methodname, method in methods.items():
                wrapped = wrap(method)
                setattr(cls_or_fn, methodname, wrapped)
            return cls_or_fn
    
    if maybe_class:
        return decorator(maybe_class)
    return decorator


PY_SITE_PKGS_RE = re.compile(r'.*(python[\d.]*)/site-packages')


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    
    # Trim paths of python libs (non-asm)
    if 'site-packages' in record.pathname:
        record.pathname = PY_SITE_PKGS_RE.sub(lambda m: f'{m.group(1)}/...', record.pathname)
    
    # Add colors (if colors are supported)
    if not hasattr(sys.stderr, "isatty") or not sys.stderr.isatty():
        return record
    
    path_stem = record.pathname.rpartition('.py')[0]
    path, _, filename = path_stem.rpartition('/')
    record.pathname = f'{path}/\x1b[38;2;200;200;200m{filename}.py\x1b[0m'
    record.funcName = f'\x1b[38;2;200;200;200m{record.funcName}\x1b[0m'
    
    levelname = record.levelname.lower()
    if levelname.startswith('warn'):
        record.levelname = f'\x1b[33m{record.levelname}\x1b[0m'
    elif levelname == 'error':
        record.levelname = f'\x1b[31m{record.levelname}\x1b[0m'
    elif levelname == 'debug':
        record.levelname = f'\x1b[35m{record.levelname}\x1b[0m'
    elif levelname == 'info':
        record.levelname = f'\x1b[36m{record.levelname}\x1b[0m'
    
    return record


def start_internal_log(microservice='-'):
    local_microservice = microservice
    level = os.getenv("SM_LOGLEVEL", logging.INFO)
    if not level:
        level = logging.INFO
    if isinstance(level, str) and level.isdigit():
        # e.g "10" → 10
        level = int(level)
    logger = logging.getLogger()
    logging.good = functools.partial(loguru_logger.success)
    logger.handlers = list()
    logger.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    sm_log_format_envvar = os.getenv('SM_LOG_FORMAT')
    if sm_log_format_envvar:
        # Example: '%(asctime)s [%(levelname)s][{microservice}][%(pathname)s:%(lineno)d][%(funcName)s()] %(message)s'
        if '{microservice}' in sm_log_format_envvar:
            log_format = sm_log_format_envvar.format(microservice=microservice)
        else:
            log_format = sm_log_format_envvar
    else:
        log_format = f'%(asctime)s\t%(levelname)s\t-\t{microservice}\t%(funcName)s\t%(message)s'
    # formatter = logging.Formatter(log_format, datefmt='%Y/%m/%d:%H:%M:%S')
    # console.setFormatter(formatter)
    console.setFormatter(Formatter(log_format, datefmt='%Y/%m/%d:%H:%M:%S'))
    logger.addHandler(console)
    logging.captureWarnings(True)
    logging.setLogRecordFactory(record_factory)
    
    logging.info("LogLevel: %s", logging.getLevelName(logging.getLogger().level))
