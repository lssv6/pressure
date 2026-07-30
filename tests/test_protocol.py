from pressure_monitor.protocol import parse_sample_line


def test_parses_comma_separated_pair():
    assert parse_sample_line("123,-456\r\n") == (123.0, -456.0)


def test_parses_other_separators():
    assert parse_sample_line("123 -456") == (123.0, -456.0)
    assert parse_sample_line("123;\t-456") == (123.0, -456.0)


def test_uses_the_last_two_fields_so_a_timestamp_is_tolerated():
    assert parse_sample_line("10452,123.5,-456.5") == (123.5, -456.5)


def test_parses_floats_and_exponents():
    assert parse_sample_line("8.3886e6,1.5") == (8388600.0, 1.5)


def test_ignores_firmware_chatter():
    assert parse_sample_line("# dual HX710B ready") is None
    assert parse_sample_line("sensor 1 not responding") is None
    assert parse_sample_line("") is None
    assert parse_sample_line("\x00\n") is None


def test_ignores_incomplete_lines():
    assert parse_sample_line("123") is None
    assert parse_sample_line("123,") is None
