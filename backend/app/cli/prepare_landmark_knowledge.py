"""Ghép receipts ảnh đã verify với facts NPS; không suy ra địa điểm từ embedding."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5


def prepare(catalog, manifest, ingestion, verification):
    if verification["status"] != "pass" or manifest.get("fixture") is not False:
        raise ValueError("VERIFIED_PUBLIC_IMAGES_REQUIRED")
    by_file = {r["filename"]: r for r in ingestion["results"] if "image_id" in r}
    source_images = {r["filename"]: r for r in manifest["images"]}
    verified = set(verification["image_ids"])
    city_id = str(uuid5(NAMESPACE_URL, "urn:phase09:city:" + catalog["city"]["name"]))
    provenance = {
        "dataset_id": catalog["dataset_id"],
        "verification": "official_source_metadata",
        "source_manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode()
        ).hexdigest(),
        "human_relevance_verified": False,
    }
    payload = {
        "fixture": False,
        "entities": [
            {
                "id": city_id,
                "canonical_name": catalog["city"]["name"],
                "entity_type": "city",
                "aliases": catalog["city"]["aliases"],
                "locale": "en",
                "external_key": "phase09:nps:city:washington-dc",
                "provenance": {**provenance, "source_ref": catalog["city"]["source_ref"]},
            }
        ],
        "relationships": [],
        "image_entities": [],
    }
    for row in catalog["images"]:
        filename = row["slug"] + ".jpg"
        record = by_file[filename]
        if record["image_id"] not in verified or filename not in source_images:
            raise ValueError("PUBLIC_IMAGE_RECEIPT_MISMATCH")
        entity_id = str(uuid5(NAMESPACE_URL, row["source_page"]))
        payload["entities"].append(
            {
                "id": entity_id,
                "canonical_name": row["canonical_name"],
                "entity_type": "landmark",
                "aliases": row["aliases"],
                "locale": "en",
                "external_key": "nps:" + row["slug"],
                "provenance": {**provenance, "source_ref": row["source_page"]},
            }
        )
        payload["relationships"].append(
            {
                "id": str(uuid5(NAMESPACE_URL, entity_id + ":located_in:" + city_id)),
                "subject_id": entity_id,
                "predicate": "located_in",
                "object_id": city_id,
                "source_ref": row["relation_source"],
                "evidence": provenance,
                "verified_at": manifest["downloaded_at"],
            }
        )
        payload["image_entities"].append(
            {
                "image_id": record["image_id"],
                "entity_id": entity_id,
                "relation": "depicts",
                "source_ref": row["download_url"],
                "verified": True,
            }
        )
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ["catalog", "manifest", "ingestion", "verification", "output"]:
        parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    payload = prepare(
        *(
            json.loads(Path(getattr(args, name)).read_text())
            for name in [
                "catalog",
                "manifest",
                "ingestion",
                "verification",
            ]
        )
    )
    with Path(args.output).open("x") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "status": "prepared_not_imported",
                "entities": len(payload["entities"]),
                "relationships": len(payload["relationships"]),
                "image_entities": len(payload["image_entities"]),
            }
        )
    )


if __name__ == "__main__":
    main()
