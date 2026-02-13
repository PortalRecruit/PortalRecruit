import re
from typing import List, Dict


CLIP_PATTERN = re.compile(r"(VS|vs)\s+([A-Za-z]+)\s*\((\d{1,2}:\d{2})\)", re.IGNORECASE)


def clean_clip_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""
    text = text.replace("P&R", "PnR")
    replacements = {
        "Post-Up > Left Block > Left Shoulder": "🏀 Post-Up (Left/Left)",
        "Post-Up > Right Block > Right Shoulder": "🏀 Post-Up (Right/Right)",
        "Post-Up > Left Block > Right Shoulder": "🏀 Post-Up (Left/Right)",
        "Post-Up > Right Block > Left Shoulder": "🏀 Post-Up (Right/Left)",
        "PnR Ball Handler > High PnR": "⚡ High PnR",
        "PnR Ball Handler > Side PnR": "⚡ Side PnR",
        "Spot-Up > No Dribble Jumper": "🎯 Catch & Shoot",
        "Spot-Up > Dribble Jumper": "🎯 Pull-Up",
        "Drives Left": "➡️ Drive Left",
        "Drives Right": "⬅️ Drive Right",
    }
    for k, v in replacements.items():
        if k in text:
            text = text.replace(k, v)
    text = re.sub(r"\s*>\s*", " > ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def analyze_tendencies(clips_list: List[str]) -> Dict[str, int]:
    totals = {
        "Drive Left": 0,
        "Drive Right": 0,
        "Left Shoulder": 0,
        "Right Shoulder": 0,
        "Catch & Shoot": 0,
        "Dribble Jumper": 0,
    }
    for clip in clips_list:
        txt = clip.lower()
        if "drive left" in txt:
            totals["Drive Left"] += 1
        if "drive right" in txt:
            totals["Drive Right"] += 1
        if "left shoulder" in txt:
            totals["Left Shoulder"] += 1
        if "right shoulder" in txt:
            totals["Right Shoulder"] += 1
        if "catch & shoot" in txt or "catch and shoot" in txt:
            totals["Catch & Shoot"] += 1
        if "dribble jumper" in txt or "pull-up" in txt:
            totals["Dribble Jumper"] += 1
    totals = {k: v for k, v in totals.items() if v > 0}
    total_actions = sum(totals.values()) or 1
    return {k: int(round((v / total_actions) * 100)) for k, v in totals.items()}


def extract_shot_locations(clips_list: List[str]) -> Dict[str, int]:
    zones = {
        "Corners": 0,
        "Wings": 0,
        "Top": 0,
        "Post": 0,
        "Paint": 0,
    }
    for clip in clips_list:
        txt = clip.lower()
        if "left corner" in txt or "right corner" in txt:
            zones["Corners"] += 1
        if "left wing" in txt or "right wing" in txt:
            zones["Wings"] += 1
        if "top of key" in txt or "high pnr" in txt or "high p&r" in txt or "high pnr" in txt:
            zones["Top"] += 1
        if "left block" in txt or "right block" in txt or "post-up" in txt or "post up" in txt:
            zones["Post"] += 1
        if "basket" in txt or "rim" in txt or "layup" in txt or "dunk" in txt:
            zones["Paint"] += 1
    zones = {k: v for k, v in zones.items() if v > 0}
    return zones


def extract_clips(player_text: str) -> List[str]:
    if not player_text:
        return []
    clips = []
    matches = list(CLIP_PATTERN.finditer(player_text))
    for i, match in enumerate(matches):
        team = match.group(2)
        clock = match.group(3)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(player_text)
        tail = player_text[start:end].strip()
        tail = tail.replace("\n", " ").replace("  ", " ").strip()
        if tail:
            tail = tail[:140]
            clips.append(f"VS {team} ({clock}) - {tail}")
        else:
            clips.append(f"VS {team} ({clock})")
    return clips
