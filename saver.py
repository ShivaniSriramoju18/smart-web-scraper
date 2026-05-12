# ============================================================
#  saver.py — Save to CSV / JSON / TXT
# ============================================================

import csv, json, os
from datetime import datetime

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def make_filename(name, ext):
    ts        = datetime.now().strftime("%Y-%m-%d_%H-%M")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return os.path.join(RESULTS_DIR, f"{safe_name}_{ts}.{ext}")

def save_csv(data, name="scraped"):
    if not data: return None
    fp = make_filename(name, "csv")
    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader(); w.writerows(data)
    print(f"  ✅ CSV  → {fp}")
    return fp

def save_json(data, name="scraped"):
    if not data: return None
    fp = make_filename(name, "json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ JSON → {fp}")
    return fp

def save_txt(data, name="scraped"):
    if not data: return None
    fp = make_filename(name, "txt")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(f"Scraped : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total   : {len(data)} items\n")
        f.write("="*50 + "\n\n")
        for i, item in enumerate(data, 1):
            f.write(f"#{i}\n")
            for k, v in item.items():
                f.write(f"  {k:<18}: {v}\n")
            f.write("\n")
    print(f"  ✅ TXT  → {fp}")
    return fp

def save_all(data, name="scraped"):
    if not data:
        print("  No data to save!"); return
    print(f"\n  💾 Saving {len(data)} items...")
    save_csv(data, name)
    save_json(data, name)
    save_txt(data, name)
    print(f"  📁 Saved in '{RESULTS_DIR}/' folder")

def load_last_json(name="scraped"):
    files = [f for f in os.listdir(RESULTS_DIR)
             if f.startswith(name) and f.endswith(".json")]
    if not files: return []
    with open(os.path.join(RESULTS_DIR, sorted(files)[-1]), encoding="utf-8") as f:
        return json.load(f)