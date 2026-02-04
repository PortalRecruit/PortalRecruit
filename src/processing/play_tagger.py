def _parse_clock_to_seconds(clock: int | str | None) -> int | None:
    if clock is None:
        return None
    if isinstance(clock, int):
        return clock
    if isinstance(clock, str):
        cleaned = clock.strip()
        if ":" in cleaned:
            minutes, _, seconds = cleaned.partition(":")
            try:
                return int(minutes) * 60 + int(seconds)
            except ValueError:
                return None
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def tag_play(description: str, clock: int | str | None = None) -> list[str]:
    """
    Analyzes a play description and game clock to assign tactical tags.
    """
    tags = set()
    desc = (description or "").lower()
    clock_seconds = _parse_clock_to_seconds(clock)

    # --- OFFENSIVE ACTIONS ---
    if "screen" in desc or "pick" in desc:
        tags.add("pnr")  # Pick and Roll
    if "isolation" in desc or "iso" in desc:
        tags.add("iso")
    if "handoff" in desc or "dho" in desc:
        tags.add("handoff")
    if "post" in desc:
        tags.add("post_up")
    if "drive" in desc:
        tags.add("drive")
    if "cut" in desc:
        tags.add("cut")

    # --- SHOT TYPES ---
    if "3pt" in desc or "3-pt" in desc or "three" in desc:
        tags.add("3pt")
        tags.add("jumpshot")
    elif "dunk" in desc:
        tags.add("dunk")
        tags.add("rim_finish")
    elif "layup" in desc:
        tags.add("layup")
        tags.add("rim_finish")
    elif "jumper" in desc or "jump shot" in desc:
        tags.add("jumpshot")

    # --- OUTCOMES ---
    if "made" in desc:
        tags.add("made")
        tags.add("score")
    elif "missed" in desc:
        tags.add("missed")
    
    if "turnover" in desc:
        tags.add("turnover")
        if "steal" in desc:
            tags.add("live_ball_turnover")
            
    if "rebound" in desc:
        tags.add("rebound")
        if "offensive" in desc:
            tags.add("oreb")
        else:
            tags.add("dreb")
            
    if "foul" in desc:
        tags.add("foul")

    # --- TRANSITION / CONTEXT ---
    if "fast break" in desc or "transition" in desc:
        tags.add("transition")
    
    # --- CLOCK SITUATIONS ---
    # Assuming clock_seconds is seconds remaining in the period
    if clock_seconds is not None:
        if 0 < clock_seconds <= 5:
            tags.add("late_clock")
        if 0 < clock_seconds <= 2:
            tags.add("buzzer_beater_scenario")

    return sorted(list(tags))
