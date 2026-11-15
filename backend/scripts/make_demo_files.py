from pathlib import Path

from scripts.seed_demo import NORTHWIND_PAGES, NOVABREW_PAGES, make_logo, make_pdf, make_poster, png

out = Path("tests/demo")
out.mkdir(parents=True, exist_ok=True)

(out / "NovaBrew_Brand_Guidelines_v4.2.pdf").write_bytes(make_pdf(NOVABREW_PAGES))
(out / "Northwind_Brand_Guidelines.pdf").write_bytes(make_pdf(NORTHWIND_PAGES))
(out / "novabrew_logo.png").write_bytes(png(make_logo()))
(out / "autumn_launch_poster.png").write_bytes(make_poster(bad=False))
(out / "summer_poster_needs_work.png").write_bytes(make_poster(bad=True))
print("Files written to tests/demo")