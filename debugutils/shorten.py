import re
import logging
from pprint import pformat

COLOR_RE = re.compile(r'(\x1b\[(?:\d;?)*m)')


def decolor(s):
    return COLOR_RE.sub('', s)


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
    args_pretty = ", ".join(map(pformat, args)) if args else ''
    kwargs_pretty = ", ".join([f'{k}={pformat(v)}' for k, v in kwargs.items()]) if kwargs else ''
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


# with open('/home/gilad/dev/allotsecure/docker-compose.yml') as f:
#     text = f.read()

# print(shorten(ascii_letters + digits + ascii_letters + digits + ascii_letters + digits))
short = shorten('12345678', 9)
print(short, f'| {len(short) = }')
assert len(short) == 8, f'{len(short) = }'
assert short == '12345678', f'{short = }'
print()

short = shorten('12345678', 8)
print(short, f'| {len(short) = }')
assert len(short) == 8, f'{len(short) = }'
assert short == '12345678', f'{short = }'
print()

short = shorten('12345678', 7)
print(short, f'| {len(short) = }')
assert len(short) == 7, f'{len(short) = }'
assert short == '1[...]8', f'{short = }'
print()

short = shorten('12345678', 6)
print(short, f'| {len(short) = }')
assert len(short) == 6, f'{len(short) = }'
assert short == '1 .. 8', f'{short = }'
print()

short = shorten('12345678', 5)
print(short, f'| {len(short) = }')
assert len(short) == 5, f'{len(short) = }'
assert short == '1...8', f'{short = }'
print()

short = shorten('12345678', 4)
print(short, f'| {len(short) = }')
assert len(short) == 4, f'{len(short) = }'
assert short == '1..8', f'{short = }'
print()

# limit too low, returns as is
short = shorten('12345678', 3)
print(short, f'| {len(short) = }')
assert len(short) == 8, f'{len(short) = }'
assert short == '12345678', f'{short = }'
print()

short = shorten('1234567890', 9)
print(short, f'| {len(short) = }')
assert len(short) == 9, f'{len(short) = }'
assert short == '1 [...] 0', f'{short = }'
print()

short = shorten('1234567890', 8)
print(short, f'| {len(short) = }')
assert len(short) == 7, f'{len(short) = }'
assert short == '1[...]0', f'{short = }'
print()

short = shorten('abcdefghijk', 10)
print(short, f'| {len(short) = }')
assert len(short) == 10, f'{len(short) = }'
assert short == 'ab [...] k', f'{short = }'
print()

short = shorten('abcdefghijk', 9)
print(short, f'| {len(short) = }')
assert len(short) == 9, f'{len(short) = }'
assert short == 'a [...] k', f'{short = }'
print()

short = shorten('\x1b[1mabcdefghijk\x1b[0m', 9)
print(short, f'| {len(short) = }')
assert len(short) == 9, f'{len(short) = }'
assert short == 'a [...] k', f'{short = }'
print()
