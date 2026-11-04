"""GTIN barcode validation and normalisation (EAN-13, EAN-8, UPC-A, UPC-E, GTIN-14)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Barcode:
    raw: str
    format: str  # EAN13 | EAN8 | UPCA | UPCE | GTIN14
    gtin14: str  # zero-padded canonical key used for duplicate detection

    @property
    def lookup_code(self) -> str:
        """Code to send to Open Food Facts (EAN-13 form where possible)."""
        if self.format == "EAN8":
            return self.raw
        return self.gtin14.lstrip("0").zfill(13) if self.gtin14.startswith("0") else self.gtin14


def gtin_check_digit(body: str) -> int:
    """GS1 mod-10 check digit for the digits *before* the check digit."""
    total = 0
    for i, ch in enumerate(reversed(body)):
        total += int(ch) * (3 if i % 2 == 0 else 1)
    return (10 - total % 10) % 10


def _valid(code: str) -> bool:
    return gtin_check_digit(code[:-1]) == int(code[-1])


def upce_to_upca(upce: str) -> str:
    """Expand an 8-digit UPC-E (number system + 6 digits + check) to 12-digit UPC-A."""
    if len(upce) != 8:
        raise ValueError("UPC-E must have 8 digits")
    ns, d, check = upce[0], upce[1:7], upce[7]
    last = d[5]
    if last in "012":
        body = d[0:2] + last + "0000" + d[2:5]
    elif last == "3":
        body = d[0:3] + "00000" + d[3:5]
    elif last == "4":
        body = d[0:4] + "00000" + d[4]
    else:
        body = d[0:5] + "0000" + last
    return ns + body + check


class InvalidBarcode(ValueError):
    pass


def parse_barcode(value: str) -> Barcode:
    code = "".join(ch for ch in value.strip() if ch.isdigit())
    if not code or len(code) != len(value.strip().replace(" ", "").replace("-", "")):
        raise InvalidBarcode("Barcode must contain digits only")
    n = len(code)
    if n == 8:
        if _valid(code):
            return Barcode(code, "EAN8", code.zfill(14))
        # Could be UPC-E with a number system digit of 0/1
        if code[0] in "01":
            upca = upce_to_upca(code)
            if _valid(upca):
                return Barcode(code, "UPCE", upca.zfill(14))
        raise InvalidBarcode("Invalid EAN-8/UPC-E check digit")
    if n == 12:
        if not _valid(code):
            raise InvalidBarcode("Invalid UPC-A check digit")
        return Barcode(code, "UPCA", code.zfill(14))
    if n == 13:
        if not _valid(code):
            raise InvalidBarcode("Invalid EAN-13 check digit")
        return Barcode(code, "EAN13", code.zfill(14))
    if n == 14:
        if not _valid(code):
            raise InvalidBarcode("Invalid GTIN-14 check digit")
        return Barcode(code, "GTIN14", code)
    raise InvalidBarcode("Unsupported barcode length (expected 8, 12, 13 or 14 digits)")
