import json
import sys
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore


API_URL = (
    "https://api-crownx.winmart.vn/plg/api/web/item/collection?pageNumber={page}&pageSize={size}"
)
PAGE_SIZE = 100
OUTPUT_FILE = "winmart_items.json"
MERGED_OUTPUT_FILE = "winmart_items_merged.json"


def fetch_page(page_number: int, page_size: int = PAGE_SIZE) -> Dict[str, Any]:
    if requests is None:
        raise RuntimeError(
            "The 'requests' package is required. Please install with: pip install requests"
        )

    url = API_URL.format(page=page_number, size=page_size)
    headers = {
        "Accept": "application/json",
        "User-Agent": "Final-Web-Project/1.0 (+https://github.com/)",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


def simplify_item(item: Dict[str, Any]) -> Dict[str, Any]:
    media_items = item.get("mediaItems") or []
    media_urls = [m.get("mediaUrl") for m in media_items if isinstance(m, dict)]
    sizes = item.get("sizes") or []

    return {
        "id": item.get("id"),
        "itemNo": item.get("itemNo"),
        "name": item.get("name"),
        "subName": item.get("subName"),
        "price": item.get("price"),
        "salePrice": item.get("salePrice"),
        "seoName": item.get("seoName"),
        "mediaUrl": item.get("mediaUrl"),
        "mediaItems": media_urls,
        "updatedDate": item.get("updatedDate"),
        "mch": {
            "mch2": item.get("mch2"),
            "mch3": item.get("mch3"),
            "mch4": item.get("mch4"),
            "mch5": item.get("mch5"),
            "mch6": item.get("mch6"),
        },
        "sizes": [
            {
                "id": s.get("id"),
                "itemNo": s.get("itemNo"),
                "name": s.get("name"),
                "size": s.get("size"),
                "baseSize": s.get("baseSize"),
                "addSalePrice": s.get("addSalePrice"),
                "mediaUrl": s.get("mediaUrl"),
            }
            for s in sizes
            if isinstance(s, dict)
        ],
    }


def _unique_preserve_order(values: List[Optional[str]]) -> List[str]:
    seen = set()
    result: List[str] = []
    for v in values:
        if not v:
            continue
        if v in seen:
            continue
        seen.add(v)
        result.append(v)
    return result


def merge_items_by_item_no(payload: Dict[str, Any]) -> Dict[str, Any]:
    def normalize_product_name(value: Optional[str]) -> Optional[str]:
        if not isinstance(value, str):
            return value
        # Remove trailing size suffixes like " (H)", " (M)", " (L)"
        return re.sub(r"\s*\((H|M|L)\)\s*$", "", value)

    items: List[Dict[str, Any]] = payload.get("items") or []
    original_total = len(items)

    grouped: Dict[str, Dict[str, Any]] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("itemNo") or item.get("id") or "__unknown__"

        existing = grouped.get(key)

        # Collect media candidates from parent and sizes
        parent_media_candidates: List[Optional[str]] = []
        parent_media_candidates.append(item.get("mediaUrl"))
        for mu in item.get("mediaItems", []) or []:
            parent_media_candidates.append(mu)
        for s in item.get("sizes", []) or []:
            if isinstance(s, dict):
                parent_media_candidates.append(s.get("mediaUrl"))

        if existing is None:
            # Initialize base record
            grouped[key] = {
                "id": item.get("id"),
                "itemNo": item.get("itemNo"),
                "name": normalize_product_name(item.get("name")),
                "subName": normalize_product_name(item.get("subName")),
                "price": item.get("price"),
                "salePrice": item.get("salePrice"),
                "seoName": item.get("seoName"),
                "mediaUrl": item.get("mediaUrl"),
                "mediaItems": _unique_preserve_order(parent_media_candidates),
                "updatedDate": item.get("updatedDate"),
                "mch": item.get("mch"),
                "sizes": [],
            }
        else:
            # Merge scalar fields with simple preference: keep earliest non-null
            for field in [
                "name",
                "subName",
                "seoName",
                "updatedDate",
            ]:
                if not existing.get(field):
                    if field in ("name", "subName"):
                        existing[field] = normalize_product_name(item.get(field))
                    else:
                        existing[field] = item.get(field)

            # For prices, keep the minimum available value to be conservative
            for price_field in ["price", "salePrice"]:
                curr = existing.get(price_field)
                newv = item.get(price_field)
                if curr is None:
                    existing[price_field] = newv
                elif isinstance(curr, (int, float)) and isinstance(newv, (int, float)):
                    existing[price_field] = min(curr, newv)

            # Merge media
            existing_media: List[str] = list(existing.get("mediaItems") or [])
            merged_media = _unique_preserve_order(existing_media + parent_media_candidates)
            existing["mediaItems"] = merged_media
            # Keep the first mediaUrl as the representative if present, otherwise first of mediaItems
            if not existing.get("mediaUrl") and merged_media:
                existing["mediaUrl"] = merged_media[0]

    # Merge sizes by size key within each grouped item
    for key, record in grouped.items():
        size_buckets: Dict[str, Dict[str, Any]] = {}
        for s in (payload.get("items") or []):
            # not used in this loop; placeholder to satisfy type hints
            pass

        # Collect sizes from all original items with the same key
        for item in items:
            if not isinstance(item, dict):
                continue
            item_key = item.get("itemNo") or item.get("id") or "__unknown__"
            if item_key != key:
                continue
            for s in item.get("sizes", []) or []:
                if not isinstance(s, dict):
                    continue
                size_key = str(s.get("size")) if s.get("size") is not None else "__none__"
                existing_bucket = size_buckets.get(size_key)
                if existing_bucket is None:
                    # Initialize bucket with current size fields
                    bucket = dict(s)
                    # Initialize computed price fields inside size
                    bucket_price = None
                    bucket_sale = None

                    # Compute candidate prices from item + size.addSalePrice
                    add_sale = s.get("addSalePrice") or 0
                    base_price = item.get("price")
                    base_sale = item.get("salePrice") if item.get("salePrice") is not None else item.get("price")

                    if isinstance(base_price, (int, float)):
                        bucket_price = base_price + (add_sale or 0)
                    if isinstance(base_sale, (int, float)):
                        bucket_sale = base_sale + (add_sale or 0)

                    if bucket_price is not None:
                        bucket["price"] = bucket_price
                    if bucket_sale is not None:
                        bucket["salePrice"] = bucket_sale

                    size_buckets[size_key] = bucket
                else:
                    # Prefer baseSize=True and keep mediaUrl if missing
                    if not existing_bucket.get("baseSize") and s.get("baseSize"):
                        existing_bucket["baseSize"] = True
                    if not existing_bucket.get("mediaUrl") and s.get("mediaUrl"):
                        existing_bucket["mediaUrl"] = s.get("mediaUrl")

                    # Update minimal price and salePrice per size across duplicates
                    add_sale = s.get("addSalePrice") or 0
                    base_price = item.get("price")
                    base_sale = item.get("salePrice") if item.get("salePrice") is not None else item.get("price")

                    if isinstance(base_price, (int, float)):
                        cand_price = base_price + (add_sale or 0)
                        if not isinstance(existing_bucket.get("price"), (int, float)):
                            existing_bucket["price"] = cand_price
                        else:
                            existing_bucket["price"] = min(existing_bucket["price"], cand_price)
                    if isinstance(base_sale, (int, float)):
                        cand_sale = base_sale + (add_sale or 0)
                        if not isinstance(existing_bucket.get("salePrice"), (int, float)):
                            existing_bucket["salePrice"] = cand_sale
                        else:
                            existing_bucket["salePrice"] = min(existing_bucket["salePrice"], cand_sale)

        # Write back merged sizes preserving deterministic order: baseSize first, then name/size
        merged_sizes = list(size_buckets.values())
        merged_sizes.sort(
            key=lambda x: (
                0 if x.get("baseSize") else 1,
                str(x.get("name") or ""),
                str(x.get("size") or ""),
            )
        )
        record["sizes"] = merged_sizes

        # Ensure mediaItems also include size mediaUrl values
        size_media_candidates = [s.get("mediaUrl") for s in merged_sizes]
        record["mediaItems"] = _unique_preserve_order(
            list(record.get("mediaItems") or []) + size_media_candidates
        )
        if not record.get("mediaUrl") and record["mediaItems"]:
            record["mediaUrl"] = record["mediaItems"][0]

    # Filter out products without media (no mediaUrl and no mediaItems)
    filtered_items: List[Dict[str, Any]] = []
    for rec in grouped.values():
        media_items = rec.get("mediaItems") or []
        has_media = bool(rec.get("mediaUrl")) or (len(media_items) > 0)
        if has_media:
            filtered_items.append(rec)
    grouped_total = len(grouped)
    removed_no_media = grouped_total - len(filtered_items)

    merged_payload = {
        "meta": {
            **(payload.get("meta") or {}),
            "merged": True,
            "totalItems": len(filtered_items),
            "originalItems": original_total,
            "groupedItems": grouped_total,
            "removedNoMedia": removed_no_media,
            "normalizations": {
                "nameSuffixRemoved": ["(H)", "(M)", "(L)"],
                "pricePerSizeComputed": True,
                "mediaDeduplicated": True,
            },
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
        "items": filtered_items,
    }
    return merged_payload


def crawl_all(max_pages: Optional[int] = None) -> Dict[str, Any]:
    page = 1
    aggregated: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {"source": "winmart", "pageSize": PAGE_SIZE}

    while True:
        payload = fetch_page(page)
        data = payload.get("data") or {}
        paging = payload.get("paging") or {}
        items = data.get("items") or []

        simplified = [simplify_item(i) for i in items if isinstance(i, dict)]
        aggregated.extend(simplified)

        has_next = bool(paging.get("hasNextPage"))

        if max_pages is not None and page >= max_pages:
            break
        if not has_next:
            break
        page += 1

    return {
        "meta": {
            **meta,
            "totalItems": len(aggregated),
            "generatedBy": "crawl_data.py",
        },
        "items": aggregated,
    }


def main() -> None:
    # Modes:
    #   default: crawl and save to OUTPUT_FILE
    #   --merge [input_json] [output_json]: merge existing JSON items by item size/media
    if len(sys.argv) > 1 and sys.argv[1] == "--merge":
        input_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_FILE
        output_path = sys.argv[3] if len(sys.argv) > 3 else MERGED_OUTPUT_FILE

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            print(f"Failed to read input JSON '{input_path}': {e}", file=sys.stderr)
            sys.exit(1)

        merged = merge_items_by_item_no(payload)

        # Console preview
        preview = {
            "meta": merged.get("meta"),
            "items": (merged.get("items") or [])[:3],
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to write merged JSON '{output_path}': {e}", file=sys.stderr)
            sys.exit(1)

        print(
            f"\nMerged {merged['meta']['totalItems']} items -> {output_path} (source: {input_path})"
        )
        return

    # default crawl flow
    try:
        result = crawl_all()
    except Exception as e:  # pragma: no cover
        print(f"Error while crawling: {e}", file=sys.stderr)
        sys.exit(1)

    preview = {
        "meta": result.get("meta"),
        "items": (result.get("items") or [])[:3],
    }
    print(json.dumps(preview, ensure_ascii=False, indent=2))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {result['meta']['totalItems']} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

