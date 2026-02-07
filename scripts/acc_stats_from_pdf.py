from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pdfplumber


@dataclass
class SectionSpec:
    name: str
    columns: list[str]


SECTION_SPECS = {
    "Scoring": SectionSpec("Scoring", ["g", "fg", "fg3", "ft", "pts", "avg"]),
    "Rebounding": SectionSpec("Rebounding", ["g", "off", "def", "total", "avg"]),
    "Free Throw Percentage": SectionSpec("Free Throw Percentage", ["g", "ftm", "fta", "pct"]),
    "Steals": SectionSpec("Steals", ["g", "no", "avg"]),
    "3-Point FG Percentage": SectionSpec("3-Point FG Percentage", ["g", "fg3", "fga3", "pct"]),
    "3-Point FG Made": SectionSpec("3-Point FG Made", ["g", "fg3", "avg"]),
    "Blocked Shots": SectionSpec("Blocked Shots", ["g", "blk", "avg"]),
    "Assist/Turnover Ratio": SectionSpec("Assist/Turnover Ratio", ["g", "ast", "to", "ratio"]),
    "Minutes Played": SectionSpec("Minutes Played", ["g", "min", "avg"]),
}

PAIR_SECTIONS = {
    "Scoring": "Rebounding",
    "Free Throw Percentage": "Steals",
    "3-Point FG Percentage": "3-Point FG Made",
    "Blocked Shots": "Assist/Turnover Ratio",
}

RANK_RE = re.compile(r"(\d+)\.\s+([^\-]+?)\s+-\s+([A-Za-z]+)\s+", re.MULTILINE)


def iter_entries(line: str) -> Iterable[tuple[str, str, str, str]]:
    """Yield (rank, player, team, trailing_text) for each ranked entry in line."""
    matches = list(RANK_RE.finditer(line))
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
        trailing = line[start:end].strip()
        yield m.group(1), m.group(2).strip(), m.group(3).strip(), trailing


def parse_numbers(text: str) -> list[str]:
    return re.findall(r"\d+\.\d+|\d+", text)


def detect_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    sections = []
    current_name = None
    buf: list[str] = []

    for line in lines:
        if not line.strip():
            continue

        header_match = None
        for key in SECTION_SPECS:
            if line.startswith(key):
                header_match = key
                break

        if header_match:
            if current_name and buf:
                sections.append((current_name, buf))
                buf = []
            current_name = header_match
            continue

        if current_name:
            buf.append(line)

    if current_name and buf:
        sections.append((current_name, buf))

    return sections


def parse_pdf(path: Path) -> list[dict]:
    records: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.splitlines()]
            sections = detect_sections(lines)

            for section_name, section_lines in sections:
                spec = SECTION_SPECS.get(section_name)
                if not spec:
                    continue

                paired = PAIR_SECTIONS.get(section_name)
                paired_spec = SECTION_SPECS.get(paired) if paired else None

                for line in section_lines:
                    if not RANK_RE.search(line):
                        continue

                    entries = list(iter_entries(line))
                    for entry_idx, (rank, player, team, trailing) in enumerate(entries):
                        active_section = section_name
                        active_spec = spec
                        if paired and entry_idx == 1:
                            active_section = paired
                            active_spec = paired_spec

                        nums = parse_numbers(trailing)
                        row = {
                            "section": active_section,
                            "rank": int(rank),
                            "player": player,
                            "team": team,
                            "values": nums,
                            "raw": trailing,
                        }
                        if active_spec and len(nums) >= len(active_spec.columns):
                            row.update({k: nums[i] for i, k in enumerate(active_spec.columns)})
                        records.append(row)

    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse ACC individual stats PDF into structured rows.")
    parser.add_argument("--pdf", required=True, help="Path to ACC stats PDF")
    parser.add_argument("--out", default="data/acc_stats_from_pdf.jsonl", help="Output JSONL path")
    args = parser.parse_args()

    path = Path(args.pdf)
    if not path.exists():
        raise FileNotFoundError(path)

    records = parse_pdf(path)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"✅ Wrote {len(records)} rows -> {out_path}")


if __name__ == "__main__":
    main()
