import inspect
import logging
import os
import re
from pprint import pformat as _pformat

try:
    termwidth = os.get_terminal_size()[0]
except:
    termwidth = 120
pformat = lambda x: _pformat(x, indent=2, width=termwidth)

OBJ_RE = re.compile(r'<(?:[\w\d<>]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')
TYPE_RE = re.compile(r"<class '(?:[\w\d<>]+\.)*([\w\d]+)'>")
WHITESPACE_RE = re.compile(r'\s+')
COLOR_RE = re.compile(r'(\x1b\[(?:\d;?)*m)')


def decolor(s):
    return COLOR_RE.sub('', s)


def shorten(s, limit=termwidth):
    if not s:
        return s
    if limit < 4:
        logging.warning(f"shorten({shorten(repr(s), limit=20)}) was called with limit = %d, can handle limit >= 4", limit)
        return s
    length = len(s)
    if length <= limit:
        return s
    half_the_limit = limit // 2
    if '\033[' in s:
        no_color = decolor(s)
        real_length = len(no_color)
        if real_length <= limit:
            return s
        color_matches: list[re.Match] = list(COLOR_RE.finditer(s))
        if len(color_matches) == 2:
            color_a, color_b = color_matches
            if color_a.start() == 0 and color_b.end() == length:
                # Colors surround string from both ends
                return f'{color_a.group()}{shorten(no_color, limit)}{color_b.group()}'
        return shorten(no_color, limit)
        # escape_seq_start_rindex = s.rindex('\033')
        # left_cutoff = max(escape_seq_start_index + 4, half_the_limit)
        # right_cutoff = min((real_length - escape_seq_start_rindex) + 4, half_the_limit)
        # print(f'{limit = } | {length = } | {real_length = } | {left_cutoff = } | {right_cutoff = } | {half_the_limit = } | {escape_seq_start_index = } | {escape_seq_start_rindex = }')
    left_cutoff = max(half_the_limit - 3, 1)
    right_cutoff = max(half_the_limit - 4, 1)
        # print(f'{limit = } | {length = } | {left_cutoff = } | {right_cutoff = } | {half_the_limit = }')
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
    return WHITESPACE_RE.sub(' ', f'{beginning}{separator}{end}')
    
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
