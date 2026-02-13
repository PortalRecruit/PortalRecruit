from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Any

from src.similarity import find_similar_players
from src.position_calibration import calculate_percentile, map_db_to_canonical
from src.archetypes import assign_archetypes


def get_secret(secret_name: str):
    try:
        from snowflake.snowpark.context import get_active_session  # noqa: F401
        import _snowflake
        return _snowflake.get_generic_secret_string(secret_name.upper())
    except Exception:
        try:
            import streamlit as st
            return st.secrets.get(secret_name.lower())
        except Exception:
            return None


try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


FALLBACK = (
    "{name} profiles as a {role} with {archetypes} traits. "
    "Physically, he sits around the {h_pct}th percentile for height and {w_pct}th percentile for weight. "
    "Production suggests {ppg} PPG and {rpg} RPG."
)


def _get_client():
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY") or get_secret("openai_api_key")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_scouting_report(player_obj: Dict[str, Any]) -> str:
    name = player_obj.get("name") or player_obj.get("player_name") or "Player"
    pos = player_obj.get("position") or ""
    mapped = map_db_to_canonical(pos)
    canonical = mapped[0] if mapped else pos
    h_in = player_obj.get("height_in")
    w_lb = player_obj.get("weight_lb")
    h_pct = calculate_percentile(h_in, pos, metric="h")
    w_pct = calculate_percentile(w_lb, pos, metric="w")

    stats = player_obj.get("stats") or {}
    ppg = stats.get("ppg") or player_obj.get("ppg") or 0
    rpg = stats.get("rpg") or player_obj.get("rpg") or 0
    apg = stats.get("apg") or player_obj.get("apg") or 0

    archetypes = assign_archetypes({"ppg": ppg, "rpg": rpg, "apg": apg, "weight_lb": w_lb}, "", pos)
    archetype_str = ", ".join(archetypes) if archetypes else "balanced"

    sims = find_similar_players(name, top_k=2)
    sim_names = [s.get("player_name") for s in sims if s.get("player_name")]
    sim_str = ", ".join(sim_names) if sim_names else "N/A"

    client = _get_client()
    if client is None:
        return FALLBACK.format(
            name=name,
            role=canonical or "prospect",
            archetypes=archetype_str,
            h_pct=h_pct,
            w_pct=w_pct,
            ppg=float(ppg) if ppg else 0,
            rpg=float(rpg) if rpg else 0,
        )

    system = (
        "You are an NCAA Assistant Coach. Write a concise, 3-paragraph scouting report. "
        "Structure: 1) Offensive Role, 2) Defensive Fit, 3) Outlook. "
        "Keep it professional and direct."
    )
    user = (
        f"Player: {name}\n"
        f"Archetypes: {archetype_str}\n"
        f"Physical percentiles: Height {h_pct}th, Weight {w_pct}th\n"
        f"Production: {ppg} PPG, {rpg} RPG, {apg} APG\n"
        f"Similar players: {sim_str}\n"
        "Write the report in Markdown."
    )

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4,
        max_tokens=450,
    )
    return resp.choices[0].message.content.strip()
