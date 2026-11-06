def rank_unique(candidates):
    output = []
    seen = set()
    for candidate in sorted(candidates, key=lambda c: (-c.score, str(c.image_id))):
        if candidate.image_id not in seen:
            output.append(candidate)
            seen.add(candidate.image_id)
    return output


def matches_metadata(filters, image, metadata, tags):
    for field in ["source_dataset", "city"]:
        expected = getattr(filters, field)
        if expected is not None and (metadata is None or getattr(metadata, field) != expected):
            return False
    if filters.media_types and image.media_type not in filters.media_types:
        return False
    if filters.tags_any and not set(tags).intersection(filters.tags_any):
        return False
    if not set(filters.tags_all).issubset(tags):
        return False
    for field in ["width", "height"]:
        low, high = getattr(filters, "min_" + field), getattr(filters, "max_" + field)
        if low is not None and getattr(image, field) < low:
            return False
        if high is not None and getattr(image, field) > high:
            return False
    captured = metadata.captured_at if metadata else None
    if filters.captured_from and (captured is None or captured < filters.captured_from):
        return False
    if filters.captured_to and (captured is None or captured > filters.captured_to):
        return False
    return True
