import sys
from pathlib import Path

DATA_RAW = Path(__file__).parent.parent / "data" / "raw"

fixed_count = 0
skipped_clean = 0
skipped_error = 0

for path in sorted(DATA_RAW.rglob("*")):
    if not path.is_file() or path.suffix not in (".shtml", ".html"):
        continue
    text = path.read_text(encoding="utf-8")
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        skipped_error += 1
        continue
    if repaired != text:
        path.write_text(repaired, encoding="utf-8")
        fixed_count += 1
        print(f"FIXED: {path.relative_to(DATA_RAW)}")
    else:
        skipped_clean += 1

print(f"\nFixed {fixed_count} files, {skipped_clean} already clean, {skipped_error} skipped (not mojibake-shaped)")
