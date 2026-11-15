"""
Builds a complete demo through the REAL API (nothing is faked):
two companies, brand knowledge extracted by the real pipeline, analysed submissions,
reviewer decisions and published sessions.

Run from backend/ with the API running:   python -m scripts.seed_demo
"""
import argparse
import io
import sys
import time
from collections import Counter

import httpx
import pymupdf
from PIL import Image, ImageDraw, ImageFont

ADMIN = ("admin", "Elena Park")
CREATOR = ("creator", "Charlie Rivera")
REVIEWER = ("reviewer", "Aria Chen")

BROWN, CREAM, FAINT = (59, 36, 24), (245, 233, 216), (170, 150, 125)

NOVABREW_PAGES = [
    """NovaBrew Brand Guidelines (v4.2)

1. About NovaBrew
NovaBrew is a specialty coffee company founded in 2012 and based in Portland, Oregon. We operate 14 cafes and roast all of our beans in Portland. Our core range is 100% certified organic.

2. Tone of Voice
Our voice is warm, friendly and confident. We speak like a knowledgeable barista, never like a salesperson. Use no more than one exclamation mark per piece of content. Never write whole sentences in capital letters.

3. Terminology
Always call the people who buy from us "coffee lovers", never "customers" or "consumers". Say "affordable" instead of "cheap". Write "NovaBrew" as one word with a capital N and B. Never write "Nova Brew" or "NOVABREW".

4. Approved Taglines
"Brew the Bold." is our primary tagline and must always include the full stop. "Roasted in Portland, loved everywhere." is approved for regional campaigns only.""",
    """5. Promotional Claim Restrictions
Never claim NovaBrew is "the best coffee in the world" or use other unprovable superlatives. Never make health claims such as "boosts immunity", "cures fatigue" or "helps you lose weight". Only describe a product as "organic" if it holds organic certification. Any discount or price claim must state the end date of the offer.

6. Visual Consistency
Our brand colours are Espresso Brown (#3B2418) and Cream (#F5E9D8). Always leave clear space around the logo equal to the height of the letter "N". The logo must never appear smaller than 30 mm wide in print. Never stretch, rotate or recolour the logo. Use only approved NovaBrew photography.

7. Accessibility
Text must have a colour contrast ratio of at least 4.5:1 against its background. Body text must be at least 12 pt in print. Every image used online needs descriptive alt text.""",
]

NORTHWIND_PAGES = [
    """Northwind Outfitters Brand Guidelines

1. Voice
We sound practical, calm and experienced, like a trail guide. Avoid hype words such as "ultimate", "extreme" and "game-changing".

2. Terminology
Call our products "gear", never "stuff". Call the people who buy from us "explorers".

3. Claims
Only describe a product as "waterproof" if it carries a waterproof rating shown on its product page. Never promise that gear is "unbreakable".

4. Approved Tagline
"Built for the long way round." is our approved tagline and must always include the full stop.

5. Company Facts
Northwind Outfitters was founded in 2009 and is based in Denver, Colorado."""
]


# ---------------------------------------------------------------- helpers
class Api:
    def __init__(self, base: str, passcode: str):
        self.client = httpx.Client(base_url=base.rstrip("/"), timeout=300)
        self.passcode = passcode

    def call(self, method, path, who, org=None, **kw):
        headers = {"X-Role": who[0], "X-User-Name": who[1]}
        if org:
            headers["X-Org-Id"] = org
        if self.passcode:
            headers["X-Demo-Key"] = self.passcode
        for attempt in range(4):
            r = self.client.request(method, path, headers=headers, **kw)
            limited = r.status_code == 502 and any(k in r.text for k in ("429", "RESOURCE_EXHAUSTED", "quota"))
            if limited and attempt < 3:
                print("   Gemini rate limit reached, waiting 45 s...")
                time.sleep(45)
                continue
            break
        if r.status_code >= 400:
            sys.exit(f"\nFAILED {method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json()


def font(size, bold=False):
    for name in (["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_logo():
    logo = Image.new("RGB", (600, 200), BROWN)
    ImageDraw.Draw(logo).text((300, 100), "NovaBrew", font=font(90, True), fill=CREAM, anchor="mm")
    return logo


def make_poster(bad: bool) -> bytes:
    logo = make_logo()
    img = Image.new("RGB", (1200, 800), CREAM)
    d = ImageDraw.Draw(img)
    if bad:
        img.paste(logo.resize((900, 110)), (150, 40))  # logo stretched on purpose
        d.text((60, 230), "NovaBrew is the BEST coffee in the world!", font=font(44, True), fill=BROWN)
        d.text((60, 330), "Our organic blend boosts your immunity", font=font(40), fill=FAINT)
        d.text((60, 420), "Nova Brew cold brew is cheap and now 30% off", font=font(36), fill=BROWN)
        d.rectangle((60, 520, 460, 650), fill=(0, 230, 0))
        d.text((260, 585), "SALE!!", font=font(64, True), fill=(255, 255, 255), anchor="mm")
        d.text((60, 700), "Brew the bold", font=font(40), fill=BROWN)
    else:
        img.paste(logo.resize((450, 150)), (60, 40))
        d.text((60, 260), "Meet our newest roast, coffee lovers.", font=font(56, True), fill=BROWN)
        d.text((60, 380), "Brew the Bold.", font=font(48), fill=BROWN)
    return png(img)


def make_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if page.insert_textbox(pymupdf.Rect(50, 50, 545, 790), text, fontsize=11, fontname="helv") < 0:
            sys.exit("Guideline text did not fit on a page")
    data = doc.tobytes()
    doc.close()
    return data


def ensure_org(api: Api, name: str) -> str:
    if any(o["name"] == name for o in api.call("GET", "/organisations", ADMIN)):
        sys.exit(f'"{name}" already exists. Remove it first (see the cleanup SQL), then run again.')
    return api.call("POST", "/organisations", ADMIN, json={"name": name})["id"]


def onboard_knowledge(api: Api, org: str, filename: str, pages: list[str]) -> list[dict]:
    """The real pipeline: upload PDF -> extract -> Gemini categorises -> admin approves -> embeddings."""
    doc = api.call("POST", "/brand-documents", ADMIN, org, files={"file": (filename, make_pdf(pages), "application/pdf")})
    doc_id = doc["id"]
    api.call("POST", f"/brand-documents/{doc_id}/extract", ADMIN, org)

    start = time.time()
    while True:
        d = api.call("GET", f"/brand-documents/{doc_id}", ADMIN, org)
        waited = int(time.time() - start)
        print(f"   extraction status: {d['status']} ({waited}s)   ", end="\r")
        if d["status"] == "extracted":
            break
        if d["status"] == "failed":
            sys.exit(f"\nExtraction failed: {d.get('error_message')}")
        if waited > 600:
            sys.exit(
                f"\nExtraction timed out. Document {doc_id} is still '{d['status']}'.\n"
                "Check the uvicorn terminal for an error, and run: python -m scripts.smoke_gemini"
            )
        time.sleep(4)
    print()

    items = api.call("GET", f"/knowledge-items?document_id={doc_id}&status=pending", ADMIN, org)
    if not items:
        sys.exit("No knowledge items were extracted")
    api.call("POST", "/knowledge-items/bulk-review", ADMIN, org,
             json={"ids": [i["id"] for i in items], "action": "approve"})

    cats = Counter(i["category"] for i in items)
    globals_ = sum(1 for i in items if i["is_global"])
    print(f"   {len(items)} items approved ({globals_} global): " + ", ".join(f"{c} {n}" for c, n in sorted(cats.items())))
    return items


def new_text(api, org, title, text) -> str:
    return api.call("POST", "/submissions", CREATOR, org, json={"title": title, "text_content": text})["id"]


def new_image(api, org, title, data) -> str:
    return api.call("POST", "/submissions/image", CREATOR, org,
                    data={"title": title}, files={"file": ("poster.png", data, "image/png")})["id"]


def analyse(api, org, sid, label):
    a = api.call("POST", f"/submissions/{sid}/analyze", CREATOR, org)
    print(f"   analysed '{label}': {a['summary'].get('total', 0)} findings")
    time.sleep(5)  # stay friendly to the Gemini rate limit


def decide(api, org, sid, decision, comment=None):
    api.call("POST", f"/submissions/{sid}/review", REVIEWER, org, json={"decision": decision, "comment": comment})


def set_visibility(api, org, sid, visibility):
    api.call("PATCH", f"/submissions/{sid}/visibility", REVIEWER, org, json={"visibility": visibility})


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--app", default="http://localhost:5173", help="frontend address (only used to print links)")
    ap.add_argument("--passcode", default="")
    args = ap.parse_args()
    api = Api(args.api, args.passcode)

    try:
        httpx.get(f"{args.api.rstrip('/')}/health", timeout=90).raise_for_status()
    except Exception as e:
        sys.exit(f"Cannot reach the API at {args.api}: {e}")

    print("Creating two companies...")
    nb = ensure_org(api, "NovaBrew Coffee")
    nw = ensure_org(api, "Northwind Outfitters")

    print("\n[1/5] NovaBrew: brand knowledge from the guidelines PDF")
    items = onboard_knowledge(api, nb, "NovaBrew_Brand_Guidelines_v4.2.pdf", NOVABREW_PAGES)
    if not {"tone", "terminology", "promotional_claims"} <= {i["category"] for i in items}:
        print("   WARNING: some expected categories are missing. Review them on the Brand Knowledge page.")

    print("\n[2/5] NovaBrew: approved logo")
    api.call("POST", "/brand-assets", ADMIN, nb, data={"asset_type": "logo", "name": "NovaBrew logo"},
             files={"file": ("logo.png", png(make_logo()), "image/png")})

    print("\n[3/5] NovaBrew: submissions (each is analysed by the real engines)")
    offer = new_text(api, nb, "Weekend Offer (draft)",
                     "BUY NOW BEFORE THIS OFFER ENDS! Our cold brew is 30% off!! Brew the bold")
    analyse(api, nb, offer, "Weekend Offer (draft)")  # stays IN REVIEW for the live reviewer demo

    roast = new_text(api, nb, "Meet our newest roast", "Meet our newest roast, coffee lovers. Brew the Bold.")
    analyse(api, nb, roast, "Meet our newest roast")
    decide(api, nb, roast, "approved")
    set_visibility(api, nb, roast, "public")

    good = new_image(api, nb, "Autumn Launch Poster", make_poster(bad=False))
    analyse(api, nb, good, "Autumn Launch Poster")
    decide(api, nb, good, "approved")
    set_visibility(api, nb, good, "public")

    bad = new_image(api, nb, "Summer Poster (needs work)", make_poster(bad=True))
    analyse(api, nb, bad, "Summer Poster (needs work)")
    decide(api, nb, bad, "changes_requested",
           "Please fix the flagged logo and contrast issues and the unsupported claims, then resubmit.")

    print("\n[4/5] Northwind Outfitters: brand knowledge")
    onboard_knowledge(api, nw, "Northwind_Brand_Guidelines.pdf", NORTHWIND_PAGES)

    print("\n[5/5] Northwind Outfitters: published sessions")
    spring = new_text(api, nw, "Spring Trail Collection",
                      "Explorers, our spring gear is ready for long days on the trail. Built for the long way round.")
    analyse(api, nw, spring, "Spring Trail Collection")
    decide(api, nw, spring, "approved")
    set_visibility(api, nw, spring, "public")

    brief = new_text(api, nw, "Retail Partner Briefing",
                     "A practical look at how our gear is tested, written for retail partners.")
    analyse(api, nw, brief, "Retail Partner Briefing")
    decide(api, nw, brief, "approved")
    set_visibility(api, nw, brief, "unlisted")
    token = api.call("GET", f"/submissions/{brief}/sharing", REVIEWER, nw)["share_token"]

    gallery = httpx.get(f"{args.api.rstrip('/')}/public/sessions", timeout=60).json()
    print("\n" + "=" * 60)
    print("DEMO READY")
    print(f"  App:            {args.app}   (choose workspace 'NovaBrew Coffee')")
    print(f"  Public gallery: {args.app}/gallery   ({gallery['total']} published sessions)")
    print(f"  Unlisted link:  {args.app}/s/{token}")
    print("=" * 60)


if __name__ == "__main__":
    main()