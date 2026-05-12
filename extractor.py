# ============================================================
#  extractor.py — Extract ALL or SPECIFIC data automatically
#  User never needs to inspect or type selectors
# ============================================================

import requests
from bs4 import BeautifulSoup
import random
from detector import fetch, extract_card_fields_auto, guess_field_name

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]


# ── Extract ALL cards — full data ────────────────────────────
def extract_all_cards(url, card_group):
    """
    Extracts every card from the page using detected pattern.
    Returns list of dicts — one per card — with all fields named.
    """
    html = fetch(url)
    if not html:
        return []

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select(card_group["selector"])

    print(f"  📦 Found {len(cards)} cards. Extracting all data...")

    all_data = []
    for card in cards:
        fields = extract_card_fields_auto(card)
        if fields:
            # Fix relative links
            if "link" in fields and not fields["link"].startswith("http"):
                base = "/".join(url.split("/")[:3])
                fields["link"] = base + fields["link"]
            all_data.append(fields)

    # Normalize — make sure all rows have same columns
    all_data = normalize_rows(all_data)
    return all_data


# ── Extract SPECIFIC fields only ────────────────────────────
def extract_specific_fields(url, card_group, wanted_fields):
    """
    Extracts all cards but keeps only the fields user picked.
    wanted_fields = ["title", "salary", "location"]
    """
    all_data = extract_all_cards(url, card_group)
    filtered = []
    for row in all_data:
        # Match fields — also check partial matches
        matched = {}
        for wanted in wanted_fields:
            # Exact match first
            if wanted in row:
                matched[wanted] = row[wanted]
            else:
                # Partial match (e.g. user picks "title", row has "title_2")
                for key in row:
                    if key.startswith(wanted):
                        matched[key] = row[key]
                        break
        if matched:
            filtered.append(matched)
    return filtered


# ── Normalize rows to same columns ──────────────────────────
def normalize_rows(data):
    """
    Makes sure every row has the same set of columns.
    Missing values filled with "N/A".
    """
    if not data:
        return data

    # Collect all unique keys across all rows
    all_keys = []
    seen = set()
    for row in data:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                all_keys.append(k)

    # Fill missing keys with N/A
    normalized = []
    for row in data:
        normalized_row = {k: row.get(k, "N/A") for k in all_keys}
        normalized.append(normalized_row)

    return normalized


# ── Extract headings ─────────────────────────────────────────
def extract_headings(url, tag_filter=None):
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    data = []
    tags = [tag_filter] if tag_filter else ["h1","h2","h3"]
    for tag in tags:
        for el in soup.find_all(tag):
            t = el.get_text(strip=True)
            if t:
                data.append({"tag": tag, "heading": t})
    return data


# ── Extract links ────────────────────────────────────────────
def extract_links(url, keyword=None):
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    base = "/".join(url.split("/")[:3])
    data = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("/"):
            href = base + href
        if not href.startswith("http") or href in seen or not text:
            continue
        seen.add(href)
        if keyword and keyword.lower() not in href.lower() \
                   and keyword.lower() not in text.lower():
            continue
        data.append({"text": text[:80], "url": href})
    return data


# ── Extract tables ───────────────────────────────────────────
def extract_tables(url):
    html = fetch(url)
    if not html:
        return []
    soup  = BeautifulSoup(html, "html.parser")
    all_rows = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        for tr in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if cols:
                row = dict(zip(headers, cols)) if len(headers) == len(cols) \
                      else {f"col_{i}": v for i, v in enumerate(cols, 1)}
                all_rows.append(row)
    return all_rows


# ── Extract paragraphs ───────────────────────────────────────
def extract_paragraphs(url, keyword=None):
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    data = []
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if not t or len(t) < 20:
            continue
        if keyword and keyword.lower() not in t.lower():
            continue
        data.append({"paragraph": t})
    return data
