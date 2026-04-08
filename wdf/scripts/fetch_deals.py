"""
WeddingDealsFinder — Automated Deal Fetcher
---------------------------------------------
Runs daily via GitHub Actions.
1. Downloads ShareASale merchant datafeeds
2. Filters for wedding-relevant deals
3. Scores and ranks by discount size
4. Writes deals.json to the site/ folder
5. GitHub Actions deploys the updated site to Netlify
"""

import os
import csv
import json
import time
import hmac
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from io import StringIO

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Set these as GitHub Actions secrets (explained in README.md)
SHAREASALE_AFFILIATE_ID = os.environ.get("SHAREASALE_AFFILIATE_ID", "")
SHAREASALE_API_TOKEN    = os.environ.get("SHAREASALE_API_TOKEN", "")
SHAREASALE_SECRET_KEY   = os.environ.get("SHAREASALE_SECRET_KEY", "")

# Wedding-relevant merchant IDs from ShareASale.
# Replace these with your real approved merchant IDs after joining ShareASale.
MERCHANT_IDS = [
    "7438",   # David's Bridal
    "38504",  # Zola
    "78464",  # Minted
    "3717",   # 1-800-Flowers
    "76525",  # Shutterfly
    "99937",  # Vistaprint
    "14171",  # Etsy
]

WEDDING_KEYWORDS = [
    "wedding", "bride", "bridal", "groom", "bridesmaid", "groomsmen",
    "engagement", "vow", "ceremony", "reception", "honeymoon",
    "bouquet", "floral", "invitation", "save the date", "registry",
    "photo book", "print", "dress", "gown", "tuxedo", "venue",
    "rehearsal", "anniversary", "bachelorette", "bachelor",
]

CATEGORY_MAP = {
    "david":        "dress",
    "bridal":       "dress",
    "zola":         "registry",
    "minted":       "invites",
    "vistaprint":   "invites",
    "flowers":      "florals",
    "floral":       "florals",
    "shutterfly":   "prints",
    "cvs":          "prints",
    "walgreens":    "prints",
    "sephora":      "beauty",
    "ulta":         "beauty",
    "kay":          "jewelry",
    "zales":        "jewelry",
    "jared":        "jewelry",
    "booking":      "honeymoon",
    "hotels":       "honeymoon",
    "expedia":      "honeymoon",
    "airbnb":       "honeymoon",
    "amazon":       "decor",
    "etsy":         "invites",
    "anthropologie":"dress",
}

CATEGORY_ICONS = {
    "dress":    "👗",
    "photo":    "📷",
    "florals":  "🌸",
    "invites":  "✉️",
    "registry": "🎁",
    "honeymoon":"✈️",
    "beauty":   "💄",
    "decor":    "🕯️",
    "catering": "🍽️",
    "jewelry":  "💍",
    "prints":   "🖨️",
    "other":    "✦",
}


# ─── SHAREASALE API ────────────────────────────────────────────────────────────

def build_signature(action, date_str):
    sig_string = f"{SHAREASALE_AFFILIATE_ID}:{date_str}:{action}:{SHAREASALE_API_TOKEN}"
    return hmac.new(
        SHAREASALE_SECRET_KEY.encode("utf-8"),
        sig_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def fetch_merchant_datafeed(merchant_id):
    date_str = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    action   = "coupons"
    sig      = build_signature(action, date_str)
    params   = urllib.parse.urlencode({
        "affiliateId": SHAREASALE_AFFILIATE_ID,
        "token":       SHAREASALE_API_TOKEN,
        "version":     "2.8",
        "action":      action,
        "merchantId":  merchant_id,
        "XMLFormat":   "1",
    })
    url = f"https://api.shareasale.com/w.cfm?{params}"
    req = urllib.request.Request(url, headers={
        "x-ShareASale-Date":      date_str,
        "x-ShareASale-Signature": sig,
        "Content-Type":           "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        return parse_csv(raw, merchant_id)
    except Exception as e:
        print(f"  Warning: could not fetch merchant {merchant_id}: {e}")
        return []


def parse_csv(raw_csv, merchant_id):
    deals = []
    reader = csv.DictReader(StringIO(raw_csv))
    for row in reader:
        deals.append({
            "merchant_id":   merchant_id,
            "merchant_name": row.get("merchantname", ""),
            "title":         row.get("coupantitle", row.get("coupontitle", "")),
            "desc":          row.get("coupondescription", ""),
            "code":          row.get("couponcode", ""),
            "discount_text": row.get("discounttype", ""),
            "discount_val":  row.get("discountamount", "0"),
            "link":          row.get("couponurl", row.get("trackingurl", "")),
            "start_date":    row.get("startdate", ""),
            "end_date":      row.get("enddate", ""),
        })
    return deals


# ─── FILTERING & SCORING ───────────────────────────────────────────────────────

def is_wedding_relevant(deal):
    text = (deal["title"] + " " + deal["desc"] + " " + deal["merchant_name"]).lower()
    return any(kw in text for kw in WEDDING_KEYWORDS)


def guess_category(deal):
    name = deal["merchant_name"].lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in name:
            return cat
    return "other"


def parse_discount_pct(deal):
    import re
    text = (deal["discount_text"] + " " + deal["title"] + " " + deal["desc"]).lower()
    matches = re.findall(r"(\d+)\s*%", text)
    if matches:
        return max(int(m) for m in matches)
    if "bogo" in text or "buy one" in text:
        return 25
    if "free shipping" in text:
        return 10
    return 0


def is_expiring_soon(deal):
    end = deal.get("end_date", "")
    if not end:
        return False
    try:
        exp = datetime.strptime(end, "%m/%d/%Y")
        return exp <= datetime.utcnow() + timedelta(hours=48)
    except Exception:
        return False


def badge_for(deal):
    pct = parse_discount_pct(deal)
    if pct >= 40:
        return "hot"
    return "new" if pct >= 20 else "deal"


# ─── DEMO DATA (used until ShareASale credentials are added) ──────────────────

DEMO_DEALS = [
    {"store":"CVS","title":"Photo prints — 50% off any order","desc":"4×6, 5×7, and 8×10 prints. Perfect for save-the-dates and invites.","discount":"50% off","category":"prints","badge":"hot","expiring":False,"icon":"🖨️","link":"#","code":"PRINT50"},
    {"store":"Zola","title":"Registry completion discount","desc":"Get 20% off everything left on your registry after the wedding.","discount":"20% off","category":"registry","badge":"new","expiring":False,"icon":"🎁","link":"#","code":""},
    {"store":"Etsy","title":"Custom wedding invitations — 15% off","desc":"Personalized stationery from thousands of independent sellers.","discount":"15% off","category":"invites","badge":"deal","expiring":False,"icon":"✉️","link":"#","code":"ETSY15"},
    {"store":"Amazon","title":"Wedding décor bundles — up to 40% off","desc":"Centerpieces, candles, fairy lights with fast Prime shipping.","discount":"Up to 40%","category":"decor","badge":"deal","expiring":False,"icon":"🕯️","link":"#","code":""},
    {"store":"Shutterfly","title":"Photo books — buy one get one free","desc":"Hardcover photo books for engagement or thank-you cards.","discount":"BOGO","category":"prints","badge":"hot","expiring":True,"icon":"📸","link":"#","code":"BOGO24"},
    {"store":"David's Bridal","title":"Bridesmaid dresses from $99","desc":"Mix and match colors and styles. Over 200 options available.","discount":"From $99","category":"dress","badge":"new","expiring":False,"icon":"👗","link":"#","code":""},
    {"store":"1-800-Flowers","title":"Wedding florals — 25% off centerpieces","desc":"Fresh centerpieces and bouquets for your ceremony and reception.","discount":"25% off","category":"florals","badge":"deal","expiring":True,"icon":"🌸","link":"#","code":"FLORAL25"},
    {"store":"Sephora","title":"Bridal beauty kits — 30% off","desc":"Full bridal makeup sets with foundation, primer, and setting spray.","discount":"30% off","category":"beauty","badge":"hot","expiring":False,"icon":"💄","link":"#","code":"BRIDE30"},
    {"store":"Booking.com","title":"Honeymoon hotels — up to 35% off","desc":"Early booking discount on select properties. Free cancellation.","discount":"35% off","category":"honeymoon","badge":"new","expiring":False,"icon":"✈️","link":"#","code":""},
    {"store":"Kay Jewelers","title":"Wedding bands — 30% off","desc":"Gold, platinum, and diamond options. Complimentary engraving.","discount":"30% off","category":"jewelry","badge":"deal","expiring":True,"icon":"💍","link":"#","code":"BAND30"},
    {"store":"Minted","title":"Save-the-dates — 20% off first order","desc":"Foil-stamped and letterpress options. Design online in minutes.","discount":"20% off","category":"invites","badge":"new","expiring":False,"icon":"✉️","link":"#","code":"MINT20"},
    {"store":"Anthropologie","title":"Bridal party gifts — 15% off","desc":"Robes, candles, and accessories for the whole bridal party.","discount":"15% off","category":"dress","badge":"deal","expiring":False,"icon":"🎁","link":"#","code":""},
]


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.utcnow().isoformat()}] WeddingDealsFinder deal fetcher starting...")

    use_demo = not (SHAREASALE_AFFILIATE_ID and SHAREASALE_API_TOKEN and SHAREASALE_SECRET_KEY)

    if use_demo:
        print("  ShareASale credentials not set — using demo data.")
        print("  Add secrets in GitHub to switch to live data (see README.md).")
        output = {
            "updated_at": datetime.utcnow().strftime("%B %d, %Y"),
            "deals":      DEMO_DEALS,
            "expiring":   [d for d in DEMO_DEALS if d["expiring"]],
            "total":      len(DEMO_DEALS),
            "mode":       "demo",
        }
    else:
        print(f"  Fetching datafeeds for {len(MERCHANT_IDS)} merchants...")
        raw_deals = []
        for mid in MERCHANT_IDS:
            print(f"  → Merchant {mid}...")
            raw_deals.extend(fetch_merchant_datafeed(mid))
            time.sleep(0.5)

        wedding_deals = [d for d in raw_deals if is_wedding_relevant(d)]
        print(f"  {len(wedding_deals)} wedding-relevant deals found.")

        formatted = []
        for d in wedding_deals:
            cat = guess_category(d)
            formatted.append({
                "store":    d["merchant_name"],
                "title":    d["title"],
                "desc":     d["desc"],
                "discount": d["discount_text"] or d["discount_val"] + "% off",
                "category": cat,
                "badge":    badge_for(d),
                "expiring": is_expiring_soon(d),
                "icon":     CATEGORY_ICONS.get(cat, "✦"),
                "link":     d["link"],
                "code":     d["code"],
            })

        formatted.sort(key=parse_discount_pct, reverse=True)

        output = {
            "updated_at": datetime.utcnow().strftime("%B %d, %Y"),
            "deals":      [d for d in formatted if not d["expiring"]][:40],
            "expiring":   [d for d in formatted if d["expiring"]][:6],
            "total":      len(formatted),
            "mode":       "live",
        }

    out_path = os.path.join(os.path.dirname(__file__), "..", "site", "deals.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Written {output['total']} deals → site/deals.json")
    print(f"  Mode: {output['mode']}")
    print("Done.")


if __name__ == "__main__":
    main()
