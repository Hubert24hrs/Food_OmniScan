"""Provider-independent product representation and HTTP helpers."""

import time
from dataclasses import dataclass, field

import httpx

from app.services.nutrition import NutritionInput


class ProviderError(Exception):
    pass


class ProviderUnavailable(ProviderError):
    """Network failure, timeout or 5xx after retries."""


class ProviderRateLimited(ProviderError):
    pass


@dataclass
class ProviderProduct:
    source: str  # off | usda
    source_id: str
    barcode: str | None
    name: str | None
    brand: str | None = None
    manufacturer: str | None = None
    categories_tags: list[str] = field(default_factory=list)
    category_label: str | None = None
    quantity: str | None = None
    serving_size: str | None = None
    countries_tags: list[str] = field(default_factory=list)
    labels_tags: list[str] = field(default_factory=list)
    packaging_text: str | None = None
    packaging_tags: list[str] = field(default_factory=list)
    ingredients_text: str | None = None
    ingredients_lang: str | None = None
    allergens_tags: list[str] = field(default_factory=list)
    traces_tags: list[str] = field(default_factory=list)
    additives_tags: list[str] = field(default_factory=list)
    analysis_tags: list[str] = field(default_factory=list)
    nova_group: int | None = None
    nutriscore_grade: str | None = None
    image_url: str | None = None
    images: dict[str, str] = field(default_factory=dict)  # kind -> url
    nutrition: NutritionInput | None = None
    url: str | None = None
    license: str | None = None
    attribution: str | None = None
    is_beverage: bool = False
    raw: dict = field(default_factory=dict)


BEVERAGE_TAGS = {
    "en:beverages",
    "en:carbonated-drinks",
    "en:sodas",
    "en:waters",
    "en:juices",
    "en:fruit-juices",
    "en:energy-drinks",
    "en:plant-based-milks",
    "en:milks",
    "en:iced-teas",
    "en:soft-drinks",
    "en:sweetened-beverages",
    "en:artificially-sweetened-beverages",
    "en:coffee-drinks",
}


def request_with_retry(client: httpx.Client, method: str, url: str, *, retries: int = 2, **kw) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = client.request(method, url, **kw)
            if r.status_code == 429:
                raise ProviderRateLimited(f"Rate limited by {httpx.URL(url).host}")
            if r.status_code >= 500:
                last = ProviderUnavailable(f"{r.status_code} from {httpx.URL(url).host}")
            else:
                return r
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = ProviderUnavailable(str(e) or e.__class__.__name__)
        if attempt < retries:
            time.sleep(0.4 * (2**attempt))
    raise last or ProviderUnavailable("unknown error")
