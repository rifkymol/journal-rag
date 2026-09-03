def format_page_ranges(pages: list[int]) -> str:
    unique_pages = sorted(
        {
            page
            for page in pages
            if isinstance(page, int) and page > 0
        }
    )

    if not unique_pages:
        return ""

    ranges: list[str] = []
    range_start = unique_pages[0]
    previous_page = unique_pages[0]

    for page in unique_pages[1:]:
        if page == previous_page + 1:
            previous_page = page
            continue

        ranges.append(
            str(range_start)
            if range_start == previous_page
            else f"{range_start}-{previous_page}"
        )
        range_start = page
        previous_page = page

    ranges.append(
        str(range_start)
        if range_start == previous_page
        else f"{range_start}-{previous_page}"
    )

    return ", ".join(ranges)


def compact_sources(sources: list[dict]) -> list[dict]:
    grouped_sources: dict[str, set[int]] = {}

    for source in sources:
        source_name = str(source.get("source") or "Unknown source")
        page = source.get("page")

        if not isinstance(page, int):
            continue

        grouped_sources.setdefault(source_name, set()).add(page)

    return [
        {
            "source": source_name,
            "pages": sorted(pages),
            "page_label": format_page_ranges(list(pages)),
        }
        for source_name, pages in grouped_sources.items()
    ]
