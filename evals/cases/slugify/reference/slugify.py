import re
import unicodedata

_SPECIAL = {"ß": "ss", "æ": "ae", "Æ": "ae", "ø": "o", "Ø": "o", "œ": "oe", "Œ": "oe"}


def slugify(text: str, max_length: int = 60) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if max_length < 1:
        raise ValueError("max_length must be at least 1")
    text = "".join(_SPECIAL.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(slug) > max_length:
        cut = slug.rfind("-", 0, max_length + 1)
        slug = (slug[:cut] if cut > 0 else slug[:max_length]).rstrip("-")
    return slug or "n-a"
