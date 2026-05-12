# ============================================================
#  detector.py — Fully Auto Detection Engine
#  Reads ANY page, finds ALL data, names fields smartly
#  Zero manual inspection needed
# ============================================================

import requests
from bs4 import BeautifulSoup
import random
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36",
]

# ── Fetch any URL ────────────────────────────────────────────
def fetch(url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return res.text
    except requests.exceptions.MissingSchema:
        print("  [Error] Invalid URL. Make sure it starts with https://")
    except requests.exceptions.ConnectionError:
        print("  [Error] Cannot connect. Check internet or URL.")
    except requests.exceptions.Timeout:
        print("  [Error] Page too slow to respond.")
    except requests.exceptions.HTTPError as e:
        print(f"  [Error] {e}")
    return None


# ── Smart field name guesser ─────────────────────────────────
def guess_field_name(text, tag="", class_name=""):
    """
    Looks at the TEXT content and class name of an element
    and guesses what kind of field it is.

    Examples:
      "Python Developer"  → title
      "TCS"               → company
      "Bangalore"         → location
      "₹6 LPA"            → salary
      "2 days ago"        → date
      "0-2 years"         → experience
      "Python, Django"    → skills
    """
    t = text.lower()
    c = class_name.lower()

    # Check class name first (most reliable)
    if any(x in c for x in ["title","heading","position","role","job-name"]):
        return "title"
    if any(x in c for x in ["company","employer","org","firm"]):
        return "company"
    if any(x in c for x in ["location","city","place","area","region"]):
        return "location"
    if any(x in c for x in ["salary","pay","wage","ctc","lpa","compensation"]):
        return "salary"
    if any(x in c for x in ["date","time","posted","ago","when"]):
        return "date_posted"
    if any(x in c for x in ["exp","experience","year"]):
        return "experience"
    if any(x in c for x in ["skill","tech","tag","keyword","stack"]):
        return "skills"
    if any(x in c for x in ["desc","about","detail","summary","content"]):
        return "description"
    if any(x in c for x in ["price","cost","amount","rate","fee"]):
        return "price"
    if any(x in c for x in ["rating","star","score","review"]):
        return "rating"
    if any(x in c for x in ["category","type","genre","dept"]):
        return "category"
    if any(x in c for x in ["author","writer","by","name","person"]):
        return "author"

    # Check text content patterns
    if re.search(r'[₹$€£]\s*[\d,]+|[\d,]+\s*(lpa|lakh|k|per\s*month|ctc)', t):
        return "salary"
    if re.search(r'\d+\s*(day|hour|week|month|year)s?\s*ago', t):
        return "date_posted"
    if re.search(r'\d+\s*-\s*\d+\s*year', t):
        return "experience"
    if re.search(r'(bangalore|mumbai|delhi|hyderabad|pune|chennai|kolkata|remote|work from home)', t):
        return "location"
    if re.search(r'(python|java|react|sql|javascript|django|flask|ml|ai|node)', t):
        return "skills"
    if re.search(r'[\d.]+\s*(out of|/)\s*[\d.]+|\d+\s*stars?', t):
        return "rating"
    if re.search(r'[₹$€£][\d,.]|\d+\s*%\s*off', t):
        return "price"

    # Tag based
    if tag in ["h1","h2","h3","h4"]:
        return "title"
    if tag in ["time"]:
        return "date_posted"

    # Length based (last resort)
    words = len(text.split())
    if words <= 5:
        return "short_text"
    elif words <= 20:
        return "medium_text"
    else:
        return "description"


# ── Extract all text elements from one card ──────────────────
def extract_card_fields_auto(card):
    """
    Given ONE card element, reads EVERY text piece inside it,
    names each one smartly, and returns as a dict.

    Example output:
    {
      "title":       "Python Developer",
      "company":     "TCS",
      "location":    "Bangalore",
      "salary":      "₹6 LPA",
      "experience":  "0-2 years",
      "date_posted": "2 days ago"
    }
    """
    fields = {}
    used_names = {}  # Track duplicates → title, title_2, title_3

    # Get all elements with text
    for el in card.find_all(True):
        text = el.get_text(strip=True)

        # Skip empty, too short, or parent containers
        if not text or len(text) < 2:
            continue
        # Skip if this element contains child elements with text
        # (avoid duplicating parent + child text)
        children_text = " ".join(c.get_text(strip=True)
                                  for c in el.find_all(True)
                                  if c.get_text(strip=True))
        if children_text and len(children_text) >= len(text) - 5:
            continue

        tag        = el.name or ""
        class_name = " ".join(el.get("class", []))

        # Guess what this field is
        field_name = guess_field_name(text, tag, class_name)

        # Handle duplicate names
        if field_name in fields:
            used_names[field_name] = used_names.get(field_name, 1) + 1
            field_name = f"{field_name}_{used_names[field_name]}"

        fields[field_name] = text[:150]

    # Also grab link if present
    link = card.find("a")
    if link and link.get("href"):
        href = link["href"]
        if not href.startswith("http"):
            href = href  # keep as-is, main.py will fix
        fields["link"] = href

    return fields


# ── Find repeated card patterns ──────────────────────────────
def find_best_cards(soup):
    """
    Finds the most repeated block pattern on the page.
    These are almost always job cards, product cards, etc.
    Returns list of card groups sorted by count.
    """
    from collections import Counter

    # Count how often each tag+class combo repeats
    pattern_counter = Counter()
    pattern_map = {}

    for el in soup.find_all(["article","div","li","section"]):
        classes = el.get("class", [])
        if not classes:
            continue
        key = f"{el.name}.{classes[0]}"
        pattern_counter[key] += 1
        if key not in pattern_map:
            pattern_map[key] = el

    # Keep patterns that appear 3+ times
    card_groups = []
    seen_keys = set()

    for key, count in pattern_counter.most_common(20):
        if count < 3:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)

        sample_el = pattern_map[key]
        fields = extract_card_fields_auto(sample_el)

        # Only keep if it has at least 2 meaningful fields
        if len(fields) >= 2:
            # Get selector from key
            parts = key.split(".")
            selector = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else parts[0]

            card_groups.append({
                "selector": selector,
                "count":    count,
                "fields":   fields,
            })

    return card_groups[:5]


# ── Main detect function ─────────────────────────────────────
def detect_all(url):
    """
    Scans any URL completely.
    Returns all detected data with smart field names
    and real sample values.
    """
    print(f"\n  🔍 Scanning page...")
    html = fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    page_title = soup.title.string.strip() if soup.title else "Unknown Page"

    # ── Find cards ───────────────────────────────────────────
    cards = find_best_cards(soup)

    # ── Find headings ────────────────────────────────────────
    headings = []
    for tag in ["h1","h2","h3"]:
        for el in soup.find_all(tag):
            t = el.get_text(strip=True)
            if t and len(t) > 2:
                headings.append({"tag": tag, "text": t[:120]})

    # ── Find links ───────────────────────────────────────────
    links = []
    seen_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if href.startswith("/"):
            base = "/".join(url.split("/")[:3])
            href = base + href
        if href.startswith("http") and text and href not in seen_links:
            seen_links.add(href)
            links.append({"text": text[:60], "url": href})

    # ── Find tables ──────────────────────────────────────────
    tables = []
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows = []
        for tr in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if cols:
                row = dict(zip(headers, cols)) if headers else \
                      {f"col_{i}": v for i, v in enumerate(cols, 1)}
                rows.append(row)
        if rows:
            tables.append(rows)

    # ── Find paragraphs ──────────────────────────────────────
    paragraphs = []
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if t and len(t) > 20:
            paragraphs.append({"text": t[:200]})

    print(f"  ✅ Scan done!")

    return {
        "page_title": page_title,
        "url":        url,
        "cards":      cards,
        "headings":   headings,
        "links":      links,
        "tables":     tables,
        "paragraphs": paragraphs,
    }
