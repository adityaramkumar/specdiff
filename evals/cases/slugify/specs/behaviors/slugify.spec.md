---
id: behaviors/slugify
version: "1.0.0"
status: approved
---

## Slugify

Module `slugify.py` exposes `slugify(text: str, max_length: int = 60) -> str`.

1. Convert accented Latin letters to their ASCII base letter (`é` -> `e`, `ß` -> `ss`,
   `Æ` -> `ae`) and lowercase the result.
2. Every run of characters that are not `a`-`z` or `0`-`9` becomes a single `-`.
3. Strip leading and trailing `-`.
4. If the result is longer than `max_length`, cut it to at most `max_length`
   characters at the last `-` that keeps it within the limit; if there is no such
   `-`, cut at exactly `max_length`. Strip any trailing `-` after cutting.
5. If the result is empty, return `"n-a"`.
6. If `max_length` is less than 1, raise `ValueError("max_length must be at least 1")`.
7. If `text` is not a `str`, raise `TypeError("text must be a string")`.
