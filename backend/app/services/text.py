import re
import unicodedata

_WS = re.compile(r"\s+")
_QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "“": '"', "”": '"', "–": "-", "—": "-", "‐": "-"})


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_term(s: str) -> str:
    """Canonical matching form: lowercase, no accents, no OFF emphasis markers, single spaces."""
    s = strip_accents(s.translate(_QUOTES)).lower()
    s = s.replace("_", " ").replace("*", " ")
    s = re.sub(r"[^\w\s&'\-/.%]", " ", s)
    return _WS.sub(" ", s).strip(" .-")


def slugify(s: str) -> str:
    s = normalize_term(s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:120]
