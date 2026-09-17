"""Fakes that keep their shape, so a model reasons about them the way it would
about the real thing: the same area code, an address that is still an
address, a name that is still a name. Deterministic under the instance key.
"""

from __future__ import annotations

import hashlib
import hmac
import re

SURNAMES = (
    "Abara", "Bettencourt", "Cardoso", "Duarte", "Ekwueme", "Fontaine", "Guerra", "Halvorsen",
    "Ibrahim", "Jansen", "Kowalski", "Lindqvist", "Moreau", "Nakamura", "Okafor", "Pereira",
    "Quintero", "Rosenthal", "Silveira", "Tremblay", "Uddin", "Vasquez", "Whitfield", "Xavier",
    "Yamada", "Zielinski", "Andersen", "Baptiste", "Castellano", "Delgado", "Eriksen", "Farah",
    "Gagnon", "Hoffmann", "Iyer", "Jorgensen", "Kaur", "Lambert", "Mbeki", "Novak",
)
STREETS = (
    "Alder", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Hawthorn", "Juniper", "Linden", "Maple",
    "Oak", "Pine", "Rowan", "Spruce", "Willow", "Aspen", "Beech", "Chestnut", "Hazel", "Poplar",
)
_STREET_SUFFIX = re.compile(r"\b(Ave(?:nue)?|St(?:reet)?|Rd|Road|Dr(?:ive)?|Blvd|Cres(?:cent)?|Way|Lane|Ln|Ct|Court|Pl(?:ace)?)\.?$", re.I)
_CA_LETTERS = "ABCEGHJKLMNPRSTVWXYZ"


def _digest(key: str, category: str, real: str, salt: int) -> bytes:
    material = f"{category}\x00{real.strip().lower()}\x00{salt}".encode("utf-8")
    return hmac.new(key.encode("utf-8"), material, hashlib.sha256).digest()


def _digits(key, category, real, n, salt=0) -> str:
    value = int.from_bytes(_digest(key, category, real, salt), "big")
    return str(value % (10 ** n)).zfill(n)


def _index(key, category, real, modulo, salt=0) -> int:
    return int.from_bytes(_digest(key, category, real, salt)[:4], "big") % modulo


def _hex(key, category, real, n, salt=0) -> str:
    return _digest(key, category, real, salt).hex()[:n]


def _phone(real: str, key: str, salt: int) -> str:
    digits = re.sub(r"\D", "", real)
    if real.strip().startswith("+") and not digits.startswith("1"):
        country = digits[:2]
        rest = _digits(key, "phone", real, len(digits) - 2, salt)
        return f"+{country} {rest}"
    local = digits[-10:] if len(digits) >= 10 else digits.rjust(10, "5")
    area, last4 = local[:3], _digits(key, "phone", real, 4, salt)
    if "(" in real:
        return f"({area}) 555-{last4}"
    if "." in real:
        return f"{area}.555.{last4}"
    if real.strip().startswith("+") or len(digits) == 11:
        return f"+1 {area} 555 {last4}" if " " in real else f"+1{area}555{last4}"
    if "-" in real:
        return f"{area}-555-{last4}"
    return f"{area}555{last4}"


def _postal(real: str, key: str, salt: int) -> str:
    compact = real.replace(" ", "").replace("-", "").upper()
    if len(compact) == 6 and compact[0].isalpha():  # Canada: keep the province letter
        d = _digest(key, "postal", real, salt)
        chars = [compact[0]]
        for i in range(1, 6):
            chars.append(str(d[i] % 10) if i % 2 else _CA_LETTERS[d[i] % len(_CA_LETTERS)])
        code = "".join(chars)
        return code[:3] + " " + code[3:] if " " in real else code
    return _digits(key, "postal", real, 5, salt)


def _street(real: str, key: str, salt: int) -> str:
    suffix = _STREET_SUFFIX.search(real.strip())
    number = str(1 + _index(key, "street", real, 999, salt))
    name = STREETS[_index(key, "street-name", real, len(STREETS), salt)]
    return f"{number} {name} {suffix.group(0) if suffix else 'Ave'}"


def fake_for(category: str, real: str, key: str, salt: int = 0) -> str:
    if category == "phone":
        return _phone(real, key, salt)
    if category == "email":
        return f"p{_hex(key, category, real, 8, salt)}@example.invalid"
    if category == "postal":
        return _postal(real, key, salt)
    if category in ("name", "surname"):
        return SURNAMES[_index(key, category, real, len(SURNAMES), salt)]
    if category in ("street", "address"):
        return _street(real, key, salt)
    if category == "ip":
        d = _digest(key, category, real, salt)
        return f"10.{d[0]}.{d[1]}.{d[2]}"
    if category == "card":
        return f"**** **** **** {_digits(key, category, real, 4, salt)}"
    return f"[{category}-{_hex(key, category, real, 6, salt)}]"


_WORD = re.compile(r"[A-Za-z]{3,}")
_STREET_WORDS = {"ave", "avenue", "st", "street", "rd", "road", "dr", "drive", "blvd", "way", "lane", "court", "place", "cres", "crescent"}


def too_close(fake: str, real: str, category: str = "") -> bool:
    """A fake that equals the real value leaks it; for names and streets, so
    does a fake that repeats one of the real value's words."""
    if fake.strip().lower() == real.strip().lower():
        return True
    if category not in ("name", "surname", "street", "address"):
        return False
    real_words = {w.lower() for w in _WORD.findall(real)} - _STREET_WORDS
    return any(w.lower() in real_words for w in _WORD.findall(fake))
