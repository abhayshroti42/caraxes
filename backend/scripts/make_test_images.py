from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("tests")
OUT.mkdir(exist_ok=True)

BROWN, CREAM = (59, 36, 24), (245, 233, 216)
FAINT = (170, 150, 125)  # low-contrast text on cream: about 2.4:1


def font(size: int, bold: bool = False):
    for name in (["arialbd.ttf", "arial.ttf"] if bold else ["arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# The approved logo: 600x200 (ratio 3.0)
logo = Image.new("RGB", (600, 200), BROWN)
ImageDraw.Draw(logo).text((300, 100), "NovaBrew", font=font(90, True), fill=CREAM, anchor="mm")
logo.save(OUT / "logo.png")

# A poster with deliberate problems
bad = Image.new("RGB", (1200, 800), CREAM)
d = ImageDraw.Draw(bad)
bad.paste(logo.resize((900, 110)), (150, 40))  # logo stretched to ratio 8.2
d.text((60, 230), "NovaBrew is the BEST coffee in the world!", font=font(44, True), fill=BROWN)
d.text((60, 330), "Our organic blend boosts your immunity", font=font(40), fill=FAINT)
d.text((60, 420), "Nova Brew cold brew is cheap and now 30% off", font=font(36), fill=BROWN)
d.rectangle((60, 520, 460, 650), fill=(0, 230, 0))
d.text((260, 585), "SALE!!", font=font(64, True), fill=(255, 255, 255), anchor="mm")
d.text((60, 700), "Brew the bold", font=font(40), fill=BROWN)
bad.save(OUT / "ad_bad.png")

# A compliant poster
good = Image.new("RGB", (1200, 800), CREAM)
d = ImageDraw.Draw(good)
good.paste(logo.resize((450, 150)), (60, 40))  # correct ratio 3.0
d.text((60, 260), "Meet our newest roast, coffee lovers.", font=font(56, True), fill=BROWN)
d.text((60, 380), "Brew the Bold.", font=font(48), fill=BROWN)
good.save(OUT / "ad_good.png")

print("Created tests/logo.png, tests/ad_bad.png, tests/ad_good.png")