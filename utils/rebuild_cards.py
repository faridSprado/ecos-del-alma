from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.render_social import generar_tarjeta_social

POSTS_DIR = ROOT / "docs" / "_posts"


def parse_frontmatter(raw: str):
    if not raw.startswith("---\n"):
        return {}, raw

    _, front, body = raw.split("---", 2)

    data = {}

    for line in front.strip().splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')

    return data, body.strip()


def build_frontmatter(data: dict[str, str]) -> str:
    order = [
        "layout",
        "title",
        "date",
        "categories",
        "tema",
        "image",
        "background_image",
    ]

    lines = ["---"]

    for key in order:
        if key in data and data[key] != "":
            value = data[key]

            if key in {"title", "tema", "image", "background_image"}:
                value = f'"{value}"'

            lines.append(f"{key}: {value}")

    lines.append("---")

    return "\n".join(lines) + "\n\n"


def post_id_from_name(path: Path) -> int:
    match = re.search(r"escrito-(\d+)", path.stem)

    if not match:
        raise ValueError(f"No pude encontrar el id en {path.name}")

    return int(match.group(1))


def main() -> None:
    posts = sorted(POSTS_DIR.glob("*.md"))

    if not posts:
        print("No hay publicaciones para reconstruir.")
        return

    for post in posts:
        raw = post.read_text(encoding="utf-8")

        data, body = parse_frontmatter(raw)

        publicacion_id = post_id_from_name(post)

        tema = (
            data.get("tema")
            or data.get("title")
            or "Ecos del Alma"
        )

        background_image = data.get("background_image")

        image = generar_tarjeta_social(
            texto=body,
            tema=tema,
            imagen_url=background_image,
            publicacion_id=publicacion_id,
        )

        data["image"] = image

        fixed = build_frontmatter(data) + body.strip() + "\n"

        post.write_text(
            fixed,
            encoding="utf-8",
        )

        print(f"Actualizado: {post.name} -> {image}")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
