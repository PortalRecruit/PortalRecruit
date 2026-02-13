import re
from typing import List


CLIP_PATTERN = re.compile(r"(VS|vs)\s+([A-Za-z]+)\s*\((\d{1,2}:\d{2})\)", re.IGNORECASE)


def extract_clips(player_text: str) -> List[str]:
    if not player_text:
        return []
    clips = []
    for match in CLIP_PATTERN.finditer(player_text):
        team = match.group(2)
        clock = match.group(3)
        clips.append(f"VS {team} ({clock})")
    return clips
