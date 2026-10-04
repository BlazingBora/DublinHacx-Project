import re
from datetime import date, timedelta

import requests

ENFORCEMENT_URL = "https://api.fda.gov/food/enforcement.json"

STOPWORDS = {
    "organic", "fresh", "with", "and", "the", "brand", "flavor",
    "flavored", "natural", "original", "classic", "select", "premium",
    "whole", "pack", "size",
}

# Older recalls are almost certainly about stock that's long gone from
# shelves, so they'd only be noise.
MAX_RECALL_AGE_DAYS = 365

CLASSIFICATION_SEVERITY = {
    "Class I": "high",
    "Class II": "medium",
    "Class III": "low",
}


def _keywords(name):
    words = re.findall(r"[a-zA-Z]{4,}", name.lower())
    return [w for w in words if w not in STOPWORDS]


def _format_date(raw):
    if not raw or len(raw) != 8:
        return raw

    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def check_food_recalls(grocery_names, limit=25, timeout=4):
    """
    Cross-references grocery item names against the FDA's public food
    recall/enforcement database (openFDA). Best-effort keyword matching,
    not a guaranteed or complete check - network issues or no matches
    just return an empty list, never raise.
    """

    keyword_map = {}

    for name in grocery_names:
        if not name:
            continue

        for keyword in _keywords(name):
            keyword_map.setdefault(keyword, set()).add(name)

    if not keyword_map:
        return []

    query_keywords = sorted(keyword_map.keys())[:15]
    query = " ".join(query_keywords)

    today = date.today()
    cutoff = (today - timedelta(days=MAX_RECALL_AGE_DAYS)).strftime("%Y%m%d")
    date_range = f"recall_initiation_date:[{cutoff} TO {today.strftime('%Y%m%d')}]"

    try:
        response = requests.get(
            ENFORCEMENT_URL,
            params={
                "search": f"product_description:({query}) AND {date_range}",
                "limit": limit,
                "sort": "recall_initiation_date:desc",
            },
            timeout=timeout,
        )

        # openFDA answers 404 when nothing matches - that's just "no recalls".
        if response.status_code == 404:
            return []

        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("\nFood recall check failed (non-fatal):", type(e).__name__, str(e))
        return []

    # Reverse map: item name -> its own keyword set, so a result only
    # counts as a match for an item if ALL of that item's significant
    # words appear (as whole words) in the recall text. Plain substring
    # matching on single short words is too noisy to be trustworthy here
    # - e.g. "cola" matches inside "chocolate", "soda" matches inside
    # unrelated "baking soda" ingredient lists, generic "beans" matches
    # any bean product. Requiring the full word set together, as whole
    # words, cuts that out almost entirely.
    item_keywords = {}
    for keyword, item_names in keyword_map.items():
        for item_name in item_names:
            item_keywords.setdefault(item_name, set()).add(keyword)

    matches = []
    seen = set()

    for result in data.get("results", []):
        # Double-check the date filter in case the API ignores it.
        if (result.get("recall_initiation_date") or "") < cutoff:
            continue

        description = (result.get("product_description") or "").lower()
        description_words = set(re.findall(r"[a-z]{4,}", description))

        matched_items = {
            item_name
            for item_name, keywords in item_keywords.items()
            if keywords and keywords.issubset(description_words)
        }

        if not matched_items:
            continue

        classification = result.get("classification")

        for item_name in matched_items:
            dedupe_key = (item_name, result.get("recall_number"))

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)

            matches.append({
                "item": item_name,
                "product_description": (result.get("product_description") or "")[:160],
                "reason": result.get("reason_for_recall"),
                "classification": classification,
                "severity": CLASSIFICATION_SEVERITY.get(classification, "medium"),
                "status": result.get("status"),
                "date": _format_date(result.get("recall_initiation_date")),
                "firm": result.get("recalling_firm"),
            })

    return matches
