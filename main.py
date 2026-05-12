# ============================================================
#  main.py — Smart Scraper v2
#
#  WHAT'S NEW vs old version:
#  ✅ Zero CSS selectors ever
#  ✅ Auto extracts & names every field
#  ✅ Shows REAL sample data for every field
#  ✅ User picks fields by NUMBER only
#  ✅ Keyword filter without inspecting
#  ✅ Email alerts for new items
#
#  HOW TO RUN:
#  python main.py
# ============================================================

import os
from detector  import detect_all
from extractor import (extract_all_cards, extract_specific_fields,
                       extract_headings, extract_links,
                       extract_tables, extract_paragraphs)
from saver     import save_all, load_last_json
from emailer   import find_new_items, send_alert


# ════════════════════════════════════════════════════════════════
def print_menu():
    print("""
╔═══════════════════════════════════════════════╗
║        🕷️  Smart Auto Scraper v2               ║
║   Zero inspection. Zero selectors. Just URLs! ║
╠═══════════════════════════════════════════════╣
║  1. 🚀 Scrape any website                     ║
║  2. 📂 View saved results                     ║
║  3. ❌ Exit                                   ║
╚═══════════════════════════════════════════════╝""")


# ════════════════════════════════════════════════════════════════
#  SHOW WHAT WAS FOUND — with real sample data
# ════════════════════════════════════════════════════════════════
def show_found(results):
    """
    Displays everything detected on the page
    with real sample values so user knows exactly
    what each option contains.
    """
    options = []

    print("""
  ╔══════════════════════════════════════════════════════╗
  ║  🔍 Here's what I found on this page:               ║
  ╚══════════════════════════════════════════════════════╝""")

    # ── Cards (most useful) ──────────────────────────────────
    for cg in results["cards"]:
        idx = len(options) + 1
        fields = cg["fields"]
        print(f"\n  [{idx}] 🃏 {cg['count']} Repeated Items detected")
        print(f"       (These are likely job cards, products, listings...)\n")
        print(f"       {'FIELD':<20} {'SAMPLE DATA FOUND'}")
        print(f"       {'─'*20} {'─'*35}")
        for field, sample in list(fields.items())[:8]:
            # Clean up sample for display
            display = sample[:45].replace("\n"," ")
            print(f"       {field:<20} {display}")
        print()
        options.append(("cards", cg))

    # ── Headings ─────────────────────────────────────────────
    if results["headings"]:
        idx = len(options) + 1
        sample = results["headings"][0]["text"][:50] if results["headings"] else ""
        print(f"  [{idx}] 📰 {len(results['headings'])} Headings")
        print(f"       Sample → \"{sample}\"")
        options.append(("headings", None))

    # ── Links ────────────────────────────────────────────────
    if results["links"]:
        idx = len(options) + 1
        sample = results["links"][0]["text"][:50] if results["links"] else ""
        print(f"\n  [{idx}] 🔗 {len(results['links'])} Links")
        print(f"       Sample → \"{sample}\"")
        options.append(("links", None))

    # ── Tables ───────────────────────────────────────────────
    if results["tables"]:
        idx = len(options) + 1
        total_rows = sum(len(t) for t in results["tables"])
        print(f"\n  [{idx}] 📋 {len(results['tables'])} Table(s)  ({total_rows} rows)")
        options.append(("tables", None))

    # ── Paragraphs ───────────────────────────────────────────
    if results["paragraphs"]:
        idx = len(options) + 1
        sample = results["paragraphs"][0]["text"][:55] if results["paragraphs"] else ""
        print(f"\n  [{idx}] 📝 {len(results['paragraphs'])} Paragraphs")
        print(f"       Sample → \"{sample}...\"")
        options.append(("paragraphs", None))

    return options


# ════════════════════════════════════════════════════════════════
#  SPECIFIC FIELD PICKER — shows real samples, user picks numbers
# ════════════════════════════════════════════════════════════════
def pick_specific_fields(card_group):
    """
    Shows all auto-detected fields with real sample data.
    User picks which ones they want by entering numbers.
    Zero inspection needed.
    """
    fields = card_group["fields"]
    field_list = list(fields.keys())

    print("""
  ╔══════════════════════════════════════════════════════════════╗
  ║  🎯 Which specific fields do you want?                      ║
  ║  I found these fields automatically with real sample data:  ║
  ╚══════════════════════════════════════════════════════════════╝
""")
    print(f"  {'#':<4} {'FIELD NAME':<20} {'SAMPLE DATA'}")
    print(f"  {'─'*4} {'─'*20} {'─'*38}")

    for i, (field, sample) in enumerate(fields.items(), 1):
        display = sample[:45].replace("\n"," ") if sample else "N/A"
        print(f"  {i:<4} {field:<20} \"{display}\"")

    print(f"\n  Type 'all' to get everything")
    print(f"  Or enter numbers separated by space (e.g. 1 3 4):")
    raw = input("  Your choice → ").strip().lower()

    if raw == "all" or raw == "":
        return field_list  # Return all fields

    chosen = []
    for x in raw.split():
        try:
            idx = int(x) - 1
            if 0 <= idx < len(field_list):
                chosen.append(field_list[idx])
        except ValueError:
            continue

    return chosen if chosen else field_list


# ════════════════════════════════════════════════════════════════
#  KEYWORD FILTER — without inspecting the page
# ════════════════════════════════════════════════════════════════
def ask_keyword_filter(data_type):
    """
    Asks if user wants to filter by keyword.
    Completely optional.
    """
    print(f"\n  🔍 Want to filter results by keyword?")
    print(f"     Example: 'python' → only items containing 'python'")
    print(f"     Press Enter to skip and get ALL results")
    kw = input("  Keyword (or press Enter to skip): ").strip()
    return kw if kw else None


# ════════════════════════════════════════════════════════════════
#  MAIN SCRAPE FLOW
# ════════════════════════════════════════════════════════════════
def smart_scrape():
    print("\n" + "─"*55)
    url = input("  Paste website URL: ").strip()
    if not url:
        return
    if not url.startswith("http"):
        url = "https://" + url

    # ── Step 1: Auto scan the entire page ───────────────────
    print("\n  ⚙️  Auto-scanning page... (no inspection needed!)")
    results = detect_all(url)
    if not results:
        print("  Could not scan page. Try another URL.")
        return

    print(f"\n  📄 Page: {results['page_title']}")

    # ── Step 2: Show everything found with real samples ──────
    options = show_found(results)
    if not options:
        print("  Nothing useful found on this page.")
        return

    # ── Step 3: User picks which data type ───────────────────
    print("\n  ─────────────────────────────────────────────────")
    try:
        pick = int(input(f"  Which do you want? Enter number (1-{len(options)}): "))
        if not 1 <= pick <= len(options):
            print("  Invalid choice.")
            return
    except ValueError:
        print("  Please enter a number.")
        return

    chosen_type, chosen_data = options[pick - 1]

    # ── Step 4: ALL data or SPECIFIC fields? ─────────────────
    print("""
  ─────────────────────────────────────────────────
  How much data do you want?
  1. ✅ ALL fields   → give me everything
  2. 🎯 SPECIFIC     → I want certain fields only
  ─────────────────────────────────────────────────""")

    try:
        mode = int(input("  Enter 1 or 2: "))
    except ValueError:
        mode = 1

    # ── Step 5: Optional keyword filter ──────────────────────
    keyword = ask_keyword_filter(chosen_type)

    # ── Step 6: Extract data ──────────────────────────────────
    data = []

    if chosen_type == "cards":
        if mode == 2:
            # Auto shows fields with samples — user picks by number
            wanted = pick_specific_fields(chosen_data)
            if wanted:
                print(f"\n  ⚙️  Extracting fields: {', '.join(wanted)}...")
                data = extract_specific_fields(url, chosen_data, wanted)
            else:
                data = extract_all_cards(url, chosen_data)
        else:
            data = extract_all_cards(url, chosen_data)

        # Apply keyword filter if given
        if keyword and data:
            before = len(data)
            data = [row for row in data
                    if any(keyword.lower() in str(v).lower()
                           for v in row.values())]
            print(f"  🔍 Keyword filter '{keyword}': {before} → {len(data)} items")

    elif chosen_type == "headings":
        tag_filter = None
        if mode == 2:
            tag_filter = input("  Filter by tag (h1 / h2 / h3 / press Enter for all): ").strip() or None
        data = extract_headings(url, tag_filter)

    elif chosen_type == "links":
        data = extract_links(url, keyword)

    elif chosen_type == "tables":
        data = extract_tables(url)

    elif chosen_type == "paragraphs":
        data = extract_paragraphs(url, keyword)

    # ── Step 7: Preview results ───────────────────────────────
    if not data:
        print("\n  No data extracted. Try a different option or keyword.")
        return

    print(f"\n  ✅ Extracted {len(data)} items!")
    print(f"\n  👁️  Preview (first 3 items):")
    print("  " + "─"*50)
    for item in data[:3]:
        for k, v in item.items():
            val = str(v)[:60] if v else "N/A"
            print(f"    {k:<20}: {val}")
        print()

    # ── Step 8: Save results ──────────────────────────────────
    save_choice = input("  Save results? (y/n): ").strip().lower()
    name = "scraped"
    if save_choice == "y":
        name = input("  File name (e.g. python_jobs): ").strip() or "scraped"
        save_all(data, name)

    # ── Step 9: Email alert ───────────────────────────────────
    print("\n  📧 Want email alerts when NEW items appear?")
    email_choice = input("  Set up email alert? (y/n): ").strip().lower()
    if email_choice == "y":
        old_data  = load_last_json(name)
        key_field = list(data[0].keys())[0] if data else "title"
        new_items = find_new_items(old_data, data, key=key_field)
        site_name = results["page_title"][:30]
        print(f"  Found {len(new_items)} new item(s) since last scrape.")
        send_alert(new_items, site_name)


# ════════════════════════════════════════════════════════════════
def view_results():
    folder = "results"
    if not os.path.exists(folder) or not os.listdir(folder):
        print("\n  No saved results yet.")
        return
    print(f"\n  📂 Saved files:")
    for i, f in enumerate(sorted(os.listdir(folder)), 1):
        size = os.path.getsize(os.path.join(folder, f))
        print(f"    {i}. {f}  ({size:,} bytes)")


# ════════════════════════════════════════════════════════════════
def main():
    print("\n  👋 Welcome to Smart Scraper v2!")
    print("  Paste any URL — fields detected automatically.")
    print("  No selectors. No inspecting. Ever.\n")

    while True:
        print_menu()
        choice = input("  Enter choice (1-3): ").strip()

        if   choice == "1": smart_scrape()
        elif choice == "2": view_results()
        elif choice == "3":
            print("\n  👋 Goodbye!\n")
            break
        else:
            print("  Enter 1, 2, or 3.")

        input("\n  Press Enter to go back to menu...")


if __name__ == "__main__":
    main()
