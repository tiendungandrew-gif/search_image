"""Tạo ảnh tổng hợp chỉ trong .cache để kiểm chứng deployment; không là dataset nghiên cứu."""

import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, choices=range(1, 101), default=6)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    folder = Path(args.output).resolve()
    if not folder.is_relative_to(Path(".cache").resolve()):
        raise ValueError("FIXTURE_OUTPUT_MUST_BE_IN_CACHE")
    folder.mkdir(parents=True, exist_ok=False)
    rows = []
    for number in range(args.offset, args.offset + args.count):
        media = ["PNG", "JPEG", "WEBP"][number % 3]
        name = f"shape-{number + 1:02d}." + {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}[media]
        with Image.new("RGB", (96, 80), ((30 + number * 20) % 256, 40, 150)) as picture:
            draw = ImageDraw.Draw(picture)
            draw.rectangle((12, 12, 36 + number, 54), fill=(230, 150, 30))
            draw.line((0, number + 5, 95, 70), fill=(20, 220, 80), width=3)
            encoded = io.BytesIO()
            picture.save(encoded, format=media)
            (folder / name).write_bytes(encoded.getvalue())
        rows.append(
            {
                "filename": name,
                "title": f"Ảnh tổng hợp kiểm thử {number + 1}",
                "caption": "Synthetic geometric shapes; no real-world semantic labels.",
                "tags": ["synthetic", "phase12"],
            }
        )
    (folder / "metadata.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    )
    print(
        json.dumps({"classification": "SYNTHETIC_DATA", "images": len(rows), "output": str(folder)})
    )


if __name__ == "__main__":
    main()
