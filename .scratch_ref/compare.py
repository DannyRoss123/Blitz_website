import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.show_parser import normalize_name

ref_text = Path(__file__).parent.joinpath("reference_paste.txt").read_text(encoding="utf-8")

anchor_re = re.compile(r"(?m)^(\d+)\t(\d{4})$")
anchors = list(anchor_re.finditer(ref_text))

ref_rows = []
for i, m in enumerate(anchors):
    as_yrs, season = int(m.group(1)), m.group(2)
    start = m.end()
    end = anchors[i + 1].start() if i + 1 < len(anchors) else len(ref_text)
    block = ref_text[start:end]
    lines = [l for l in block.split("\n") if l.strip() != ""]
    if not lines:
        continue
    name = lines[0].strip()
    idx = 1
    # pos line contains a middle dot
    pos_line = lines[idx] if idx < len(lines) and "·" in lines[idx] else None
    if pos_line:
        idx += 1
    type_line_idx = None
    for j in range(idx, len(lines)):
        first_tok = lines[j].split("\t")[0].strip()
        if first_tok in ("batting", "pitching"):
            type_line_idx = j
            break
    if type_line_idx is None:
        continue
    stat_type = lines[type_line_idx].split("\t")[0].strip()
    remainder = "\n".join(lines[type_line_idx + 1:])
    tokens = [t for t in re.split(r"[\t\n]+", remainder.strip()) if t != ""]
    if len(tokens) < 4:
        continue
    team_name = tokens[0]
    team_abbr = tokens[1]
    record = tokens[2]
    k = 3
    ovr = rank = pot = None
    if tokens[k] != "—":  # em dash = no show match
        ovr = tokens[k]
        k += 1
        rankpot = tokens[k]
        rm = re.match(r"#(\d+)\s*·\s*POT\s*([A-Z])", rankpot)
        if rm:
            rank, pot = rm.group(1), rm.group(2)
        k += 1
    key_stats = tokens[k] if k < len(tokens) else ""

    ref_rows.append({
        "as_yrs": as_yrs, "season": season, "name": name, "stat_type": stat_type,
        "team_name": team_name, "team_abbr": team_abbr, "record": record,
        "ovr": ovr, "rank": rank, "pot": pot, "key_stats": key_stats,
        "norm_name": normalize_name(name),
    })

print(f"Parsed {len(ref_rows)} reference rows from {len(anchors)} anchors")

# Load our CSV
csv_rows = list(csv.DictReader(open(Path(__file__).parent.parent / "data/output/all_stars_2024_2026.csv", encoding="utf-8")))
by_key = {}
for r in csv_rows:
    key = (normalize_name(r["full_name"] or ""), r["season_id"], r["stat_type"])
    by_key.setdefault(key, []).append(r)

matched = 0
missing = []
stat_mismatches = []
record_mismatches = []
as_yrs_mismatches = []

def parse_key_stats(stat_type, key_stats):
    if stat_type == "batting":
        m = re.search(r"HR (\S+) . OPS (\S+) . OPS\+ (\S+)", key_stats)
        if m:
            return {"HR": m.group(1), "OPS": m.group(2), "OPS+": m.group(3)}
    else:
        m = re.search(r"W (\S+) . ERA (\S+) . SO (\S+) . WHIP (\S+)", key_stats)
        if m:
            return {"W": m.group(1), "ERA": m.group(2), "SO": m.group(3), "WHIP": m.group(4)}
    return {}

for ref in ref_rows:
    key = (ref["norm_name"], ref["season"], ref["stat_type"])
    candidates = by_key.get(key)
    if not candidates:
        missing.append(ref)
        continue
    # if multiple (traded), just compare against the one matching team_abbr loosely, else first
    row = candidates[0]
    if len(candidates) > 1:
        for c in candidates:
            if c["team_id"] == ref["team_abbr"] or ref["team_abbr"] in (c["team_id"] or ""):
                row = c
                break
    matched += 1

    if str(row["all_star_selections_2024_2026"]) != str(ref["as_yrs"]):
        as_yrs_mismatches.append((ref["name"], ref["season"], ref["as_yrs"], row["all_star_selections_2024_2026"]))

    if row["team_record"] and ref["record"] and row["team_record"] != ref["record"]:
        record_mismatches.append((ref["name"], ref["season"], ref["team_abbr"], ref["record"], row["team_id"], row["team_record"]))

    exp_stats = parse_key_stats(ref["stat_type"], ref["key_stats"])
    for stat_name, exp_val in exp_stats.items():
        col = {"HR": "bat_HR", "OPS": "bat_OPS", "OPS+": "bat_OPS_plus",
               "W": "pit_W", "ERA": "pit_ERA", "SO": "pit_SO", "WHIP": "pit_WHIP"}[stat_name]
        got_val = row.get(col) or "—"
        if exp_val == "—":
            continue  # ref shows dash for empty/near-empty stat lines; skip strict compare
        if got_val != exp_val:
            stat_mismatches.append((ref["name"], ref["season"], ref["stat_type"], stat_name, exp_val, got_val))

print(f"\nMatched (name+season+stat_type found in our CSV): {matched}/{len(ref_rows)}")
print(f"Missing from our CSV entirely: {len(missing)}")
for m in missing:
    print(f"  MISSING: {m['name']} {m['season']} {m['stat_type']} ({m['team_abbr']})")

print(f"\nall_star_selections mismatches: {len(as_yrs_mismatches)}")
for m in as_yrs_mismatches[:20]:
    print(f"  {m}")

print(f"\nteam_record mismatches: {len(record_mismatches)}")
for m in record_mismatches[:20]:
    print(f"  {m}")

print(f"\nkey stat mismatches: {len(stat_mismatches)}")
for m in stat_mismatches[:40]:
    print(f"  {m}")

# rows in our CSV with no reference counterpart
ref_keys = {(r["norm_name"], r["season"], r["stat_type"]) for r in ref_rows}
extra = [r for r in csv_rows if (normalize_name(r["full_name"] or ""), r["season_id"], r["stat_type"]) not in ref_keys]
print(f"\nOur CSV rows with no reference counterpart: {len(extra)}")
for r in extra[:40]:
    print(f"  EXTRA: {r['full_name']} {r['season_id']} {r['stat_type']} ({r['team_id']})")
