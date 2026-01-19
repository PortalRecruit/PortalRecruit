def tag_play(description: str, clock: str | None = None) -> list[str]:
    tags = set()
    desc = (description or "").lower()

    # Offensive structure
    if "screen" in desc or "pick" in desc:
        tags.add("pnr")
    if "isolation" in desc or "iso" in desc:
        tags.add("iso")
    if "handoff" in desc:
        tags.add("handoff")
    if "post" in desc:
        tags.add("post_up")
    if "cut" in desc:
        tags.add("cut")

    # Shot type
    if "3" in desc or "three" in desc:
        tags.add("three_point")
    if "jumper" in desc or "pull-up" in desc:
        tags.add("midrange")
    if "layup" in desc:
        tags.add("layup")
    if "dunk" in desc:
        tags.add("dunk")
    if "rim" in desc:
        tags.add("rim")

    # Outcome
    if "made" in desc:
        tags.add("made")
    if "missed" in desc:
        tags.add("missed")
    if "turnover" in desc:
        tags.add("turnover")
    if "foul" in desc:
        tags.add("foul")
    if "and-one" in desc:
        tags.add("and_one")

    # Context
    if "fast break" in desc or "transition" in desc:
        tags.add("transition")

    if clock:
        try:
            minutes, seconds = map(int, clock.split(":"))
            if minutes == 0 and seconds <= 5:
                tags.add("late_clock")
        except Exception:
            pass

    return sorted(tags)
