import re
from typing import List


CLIP_PATTERN = re.compile(r"(VS|vs)\s+([A-Za-z]+)\s*\((\d{1,2}:\d{2})\)", re.IGNORECASE)


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
            tail = tail[:120]
            clips.append(f"VS {team} ({clock}) - {tail}")
        else:
            clips.append(f"VS {team} ({clock})")
    return clips
