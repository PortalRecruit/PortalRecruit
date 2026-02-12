from __future__ import annotations

import csv
import io
from typing import Any, Dict, List


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _height_inches(val: Any) -> str:
    try:
        if isinstance(val, str) and "'" in val:
            feet, inches = val.replace("\"", "").split("'")
            return str(int(feet) * 12 + int(inches))
        return str(int(float(val)))
    except Exception:
        return ""


def generate_synergy_csv(roster_list: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["First Name", "Last Name", "Team", "Jersey", "Position", "Height", "Weight", "Class", "Notes"])
    for p in roster_list:
        name = p.get("name") or p.get("Player") or p.get("player_name") or ""
        first, last = _split_name(str(name))
        team = p.get("team") or p.get("Team") or p.get("team_id") or ""
        jersey = p.get("jersey") or p.get("Jersey") or ""
        pos = p.get("position") or p.get("Position") or ""
        height = _height_inches(p.get("height_in") or p.get("Height") or "")
        weight = p.get("weight_lb") or p.get("Weight") or ""
        clazz = p.get("class_year") or p.get("Class") or ""
        notes = p.get("notes") or ""
        writer.writerow([first, last, team, jersey, pos, height, weight, clazz, notes])
    return output.getvalue()


def generate_text_report(roster_list: List[Dict[str, Any]]) -> str:
    lines = ["PortalRecruit Shortlist Report", "-" * 32]
    for p in roster_list:
        name = p.get("name") or p.get("Player") or p.get("player_name") or "Unknown"
        team = p.get("team") or p.get("Team") or p.get("team_id") or ""
        pos = p.get("position") or p.get("Position") or ""
        height = p.get("height_in") or p.get("Height") or ""
        weight = p.get("weight_lb") or p.get("Weight") or ""
        lines.append(f"{name} | {team} | {pos} | {height} in | {weight} lb")
    return "\n".join(lines)
