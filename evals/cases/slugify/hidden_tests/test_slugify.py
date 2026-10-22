import pytest
from slugify import slugify


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, World!", "hello-world"),
        ("  Crème brûlée  ", "creme-brulee"),
        ("Straße & Æon", "strasse-aeon"),
        ("a---b___c", "a-b-c"),
        ("--Already-Slugged--", "already-slugged"),
        ("2024 Report v2.1", "2024-report-v2-1"),
        ("!!!", "n-a"),
        ("", "n-a"),
    ],
)
def test_basic(text, expected):
    assert slugify(text) == expected


def test_cuts_at_last_separator_within_limit():
    assert slugify("one two three four", max_length=13) == "one-two-three"
    assert slugify("one two three four", max_length=12) == "one-two"


def test_cuts_hard_without_separator():
    assert slugify("abcdefghij", max_length=4) == "abcd"


def test_invalid_max_length():
    with pytest.raises(ValueError, match="^max_length must be at least 1$"):
        slugify("x", max_length=0)


def test_non_string():
    with pytest.raises(TypeError, match="^text must be a string$"):
        slugify(42)
