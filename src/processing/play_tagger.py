import re

def tag_play(description: str, clock: str | None = None) -> list[str]:
    """
    Parses a play description and clock time to generate tactical tags.
    """
    tags = set()
    desc = (description or "").lower()

    # --- OFFENSIVE ACTION ---
    if "screen" in desc or "pick" in desc:
        tags.add("pnr")  # Pick and Roll
    if "isolation" in desc or "iso" in desc:
        tags.add("iso")
    if "handoff" in desc or "dho" in desc:
        tags.add("handoff")
    if "post" in desc:
        tags.add("post_up")
    if "cut" in desc:
        tags.add("cut")
    if "drive" in desc:
        tags.add("drive")

    # --- SHOT TYPE ---
    if "3pt" in desc or "3-pt" in desc or "three" in desc:
        tags.add("3pt")
    elif "dunk" in desc:
        tags.add("dunk")
        tags.add("rim_finish")
    elif "layup" in desc:
        tags.add("layup")
        tags.add("rim_finish")
    elif "jumper" in desc or "jump shot" in desc:
        tags.add("jumpshot")

    # --- OUTCOME ---
    if "made" in desc:
        tags.add("made")
        tags.add("score")
    elif "missed" in desc:
        tags.add("missed")
    
    if "turnover" in desc:
        tags.add("turnover")
    if "rebound" in desc:
        tags.add("rebound")
        if "offensive" in desc:
            tags.add("oreb")
        else:
            tags.add("dreb")
    if "foul" in desc:
        tags.add("foul")

    # --- CONTEXT ---
    if "fast break" in desc or "transition" in desc:
        tags.add("transition")
    
    # Clock Situations (e.g., Late Clock < 5 seconds)
    if clock:
        try:
            # Clock format expected: MM:SS
            parts = clock.split(":")
            if len(parts) == 2:
                minutes, seconds = int(parts[0]), int(parts[1])
                if minutes == 0 and seconds <= 5:
                    tags.add("late_clock")
                if minutes == 0 and seconds <= 2:
                    tags.add("buzzer_beater_scenario")
        except Exception:
            pass

    return sorted(list(tags))
