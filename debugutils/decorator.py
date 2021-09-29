import functools
import inspect
import logging
import os
import re
import sys
from functools import partialmethod

from loguru import logger as loguru_logger

from debugutils.format import pretty_signature_old, shorten, pretty_repr, pretty_signature

loguru_logger.level("title", no=25, color='<bold><white>')

loguru_logger.__class__.title = partialmethod(loguru_logger.__class__.log, "title")

try:
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
     A class or function decorator, logs when a method is called, and when it returns (with args and return values).

     Examples:
         
         # Ex. 1
         @log_method_calls
         class Calculator:
             def add(self, a, b): return a+b

         # Ex. 2
         @log_method_call(only=['add'])
         class ProCalculator:
             def add(self, a, b): return a + b
             def divide(self, a, b): return a / b
         
         # Ex. 3
         @log_method_calls
         def say_hello(name): print(f'Hello, {name}!')

     Args:
         only: Optionally specify `only=['some_method', 'other_method']` to only log specific methods.
         exclude: Optionally specify `exclude=['dont_care']` to skip specific methods.
     """
    cyan = lambda s: f'\033[2;3;36m{s}\033[0m'
    
    def decorator(cls_or_fn):
        def wrap(_method):
            def inner(*args, **kwargs):
                pretty_sig = pretty_signature(_method, *args, **kwargs)
                print('\n' + cyan('Calling: ') + f'{pretty_sig}\n')
                rv = _method(*args, **kwargs)
                print(f'\t {shorten(pretty_sig)} ' + cyan('Returning:\n\t → ') + pretty_repr(rv) + '\n')
                return rv
            
            return inner
        
        if inspect.isfunction(cls_or_fn):
            return wrap(cls_or_fn)
        
        if only:
            condition = lambda x: x in only
        elif exclude:
            condition = lambda x: x not in exclude
        else:
            condition = lambda x: True
        
        
        methods = {v: attr for v, attr in vars(cls_or_fn).items()
                   if inspect.isfunction(attr) and condition(v)} # todo: inspect.ismethod?
        
        for methodname, method in methods.items():
            wrapped = wrap(method)
            setattr(cls_or_fn, methodname, wrapped)
        return cls_or_fn

    if maybe_class:
        return decorator(maybe_class)
    return decorator


PY_SITE_PKGS_RE = re.compile(r'.*(python[\d.]*)/site-packages')
old_factory = logging.getLogRecordFactory()


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
    console.setFormatter(Formatter(log_format, datefmt='%Y/%m/%d:%H:%M:%S'))
    logger.addHandler(console)
    logging.captureWarnings(True)
    logging.setLogRecordFactory(record_factory)
    
    logging.info("LogLevel: %s", logging.getLevelName(logging.getLogger().level))
