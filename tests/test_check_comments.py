from scripts.check_comments import check_source


def test_clean_source_passes():
    src = '"""Module doc."""\n\n# one line\nx = 1  # inline\n'
    assert check_source(src) == []


def test_cyrillic_comment_fails():
    errors = check_source("# привет\nx = 1\n")
    assert len(errors) == 1
    assert "non-English comment" in errors[0]


def test_cyrillic_docstring_fails():
    src = 'def f():\n    """Привет."""\n'
    assert any("non-English docstring" in e for e in check_source(src))


def test_three_line_comment_block_fails():
    errors = check_source("# a\n# b\n# c\nx = 1\n")
    assert len(errors) == 1
    assert "3 lines" in errors[0]


def test_two_line_comment_block_passes():
    assert check_source("# a\n# b\nx = 1\n") == []


def test_blank_line_splits_blocks():
    assert check_source("# a\n# b\n\n# c\nx = 1\n") == []


def test_long_docstring_fails():
    src = 'def f():\n    """Line one.\n\n    Line two.\n    Line three.\n    """\n'
    assert any("docstring is" in e for e in check_source(src))


def test_two_line_docstring_passes():
    src = 'def f():\n    """Line one.\n\n    Line two.\n    """\n'
    assert check_source(src) == []


def test_directives_are_ignored():
    assert check_source("x = 1  # noqa: E501 привет\n") == []


def test_symbols_and_emoji_are_allowed():
    assert check_source("# arrow → and emoji 🏠 are fine\nx = 1\n") == []


def test_inline_comments_do_not_form_blocks():
    assert check_source("a = 1  # x\nb = 2  # y\nc = 3  # z\n") == []
