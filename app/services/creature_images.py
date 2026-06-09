from pathlib import Path
from urllib.parse import quote


_DATA_IMAGE_DIR = Path(__file__).resolve().parents[1] / "static" / "img" / "Data"
_STATIC_DATA_URL = "/static/img/Data"
_FALLBACK_CREATURE_IMAGE = f"{_STATIC_DATA_URL}/{quote('虛弱兔.png')}"


def _image_url(filename: str) -> str:
    return f"{_STATIC_DATA_URL}/{quote(filename)}"


def _load_creature_image_map() -> dict[str, str]:
    if not _DATA_IMAGE_DIR.exists():
        return {}

    image_map = {}
    for image_path in _DATA_IMAGE_DIR.iterdir():
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue

        creature_name = image_path.stem.strip()
        if creature_name:
            image_map[creature_name] = _image_url(image_path.name)

    return image_map


CREATURE_IMAGE_URLS = _load_creature_image_map()


def get_creature_image_url(name: str | None, fallback: str = _FALLBACK_CREATURE_IMAGE) -> str:
    if not name:
        return fallback

    return CREATURE_IMAGE_URLS.get(name.strip(), fallback)
