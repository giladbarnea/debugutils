from debugutils.format import shorten

def test_shorten():
    short = shorten('12345678', 9)
    assert len(short) == 8, f'{len(short) = }'
    assert short == '12345678', f'{short = }'
    
    short = shorten('12345678', 8)
    assert len(short) == 8, f'{len(short) = }'
    assert short == '12345678', f'{short = }'
    
    short = shorten('12345678', 7)
    assert len(short) == 7, f'{len(short) = }'
    assert short == '1[...]8', f'{short = }'
    
    short = shorten('12345678', 6)
    assert len(short) == 6, f'{len(short) = }'
    assert short == '1 .. 8', f'{short = }'
    
    short = shorten('12345678', 5)
    assert len(short) == 5, f'{len(short) = }'
    assert short == '1...8', f'{short = }'
    
    short = shorten('12345678', 4)
    assert len(short) == 4, f'{len(short) = }'
    assert short == '1..8', f'{short = }'
    
    # limit too low, returns as is
    short = shorten('12345678', 3)
    assert len(short) == 8, f'{len(short) = }'
    assert short == '12345678', f'{short = }'
    
    short = shorten('1234567890', 9)
    assert len(short) == 9, f'{len(short) = }'
    assert short == '1 [...] 0', f'{short = }'
    
    short = shorten('1234567890', 8)
    assert len(short) == 7, f'{len(short) = }'
    assert short == '1[...]0', f'{short = }'
    
    short = shorten('abcdefghijk', 10)
    assert len(short) == 10, f'{len(short) = }'
    assert short == 'ab [...] k', f'{short = }'
    
    short = shorten('abcdefghijk', 9)
    assert len(short) == 9, f'{len(short) = }'
    assert short == 'a [...] k', f'{short = }'


def test_shorten_with_surrounding_color():
    short = shorten('\x1b[1m1234567890\x1b[0m', 10)
    assert len(short) == 18, f'{len(short) = }'
    assert short == '\x1b[1m1234567890\x1b[0m', f'{short = }'

    short = shorten('\x1b[1m1234567890\x1b[0m', 9)
    assert len(short) == 17, f'{len(short) = }'
    assert short == '\x1b[1m1 [...] 0\x1b[0m', f'{short = }'

    short = shorten('\x1b[1m1234567890\x1b[0m', 8)
    assert len(short) == 15, f'{len(short) = }'
    assert short == '\x1b[1m1[...]0\x1b[0m', f'{short = }'


def test_shorten_with_color_inside():
    # Expect shorten to just remove the color unintelligently
    short = shorten('123\x1b[1m4567890\x1b[0m', 9)
    assert len(short) == 9, f'{len(short) = }'
    assert short == '1 [...] 0', f'{short = }'
