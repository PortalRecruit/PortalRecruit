"""
pages/99_Egress_Smoke_Test.py

Snowflake Streamlit egress/connectivity smoke test.
- Confirms Snowflake session context (db/schema/role).
- Makes HTTPS requests to allowed hosts to validate External Access Integration + Network Rules.

Success criteria:
- Any HTTP response (including 401/403/404) == network path works.
- Exceptions/timeouts == egress still blocked or DNS/host not allowed.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import streamlit as st

try:
    import requests
except Exception as exc:  # pragma: no cover
    requests = None
    _requests_import_error = exc
else:
    _requests_import_error = None

try:
    from snowflake.snowpark.context import get_active_session
except Exception:
    get_active_session = None


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    needs_auth: bool = False


def _get_secret(name: str) -> Optional[str]:
    """
    Returns a secret value if present.
    Tries:
      1) st.secrets[name]
      2) st.secrets["snowflake"][name] (some people nest)
      3) env var name
    """
    if name in st.secrets:
        return str(st.secrets[name])
    if "snowflake" in st.secrets and name in st.secrets["snowflake"]:
        return str(st.secrets["snowflake"][name])
    return os.getenv(name)


def _session_context() -> dict[str, str]:
    if get_active_session is None:
        return {"error": "snowflake.snowpark not available in this runtime"}
    session = get_active_session()
    row = session.sql(
        "SELECT CURRENT_ROLE() AS role, CURRENT_DATABASE() AS db, CURRENT_SCHEMA() AS schema, CURRENT_WAREHOUSE() AS wh"
    ).collect()[0]
    return {"role": row["ROLE"], "db": row["DB"], "schema": row["SCHEMA"], "wh": row["WH"]}


def _probe(
    target: Target,
    timeout_seconds: float,
    openai_key: Optional[str],
    serper_key: Optional[str],
    sportradar_key: Optional[str],
) -> dict[str, str]:
    if requests is None:
        return {
            "target": target.name,
            "url": target.url,
            "ok": "false",
            "status": "",
            "latency_ms": "",
            "detail": f"requests import failed: {_requests_import_error}",
        }

    headers: dict[str, str] = {"User-Agent": "snowflake-streamlit-egress-smoke-test"}

    # Auth headers are optional; non-2xx still proves connectivity
    if "api.openai.com" in target.url and openai_key:
        headers["Authorization"] = f"Bearer {openai_key}"
    if "google.serper.dev" in target.url and serper_key:
        headers["X-API-KEY"] = serper_key
        headers["Content-Type"] = "application/json"
    if "api.sportradar.com" in target.url and sportradar_key:
        # SportRadar often uses an api_key query param; we keep this as headerless connectivity
        # If you want a real endpoint test, add ?api_key=... to the URL.
        pass

    start = time.time()
    try:
        # Prefer GET (some hosts block HEAD)
        resp = requests.get(target.url, headers=headers, timeout=timeout_seconds)
        latency_ms = int((time.time() - start) * 1000)
        return {
            "target": target.name,
            "url": target.url,
            "ok": "true",
            "status": str(resp.status_code),
            "latency_ms": str(latency_ms),
            "detail": (resp.text[:200] or "").replace("\n", " ").strip(),
        }
    except Exception as exc:  # pragma: no cover
        latency_ms = int((time.time() - start) * 1000)
        return {
            "target": target.name,
            "url": target.url,
            "ok": "false",
            "status": "",
            "latency_ms": str(latency_ms),
            "detail": repr(exc),
        }


def main() -> None:
    st.set_page_config(page_title="Egress Smoke Test", layout="wide")
    st.title("Egress Smoke Test (Snowflake Streamlit)")

    with st.expander("Session context", expanded=True):
        st.json(_session_context())

    st.markdown("### Targets")
    targets = [
        Target("OpenAI (models endpoint)", "https://api.openai.com/v1/models", needs_auth=True),
        Target("Serper (host)", "https://google.serper.dev/"),
        Target("GitHub API", "https://api.github.com/"),
        Target("HuggingFace", "https://huggingface.co/"),
        Target("SportRadar (Synergy)", "https://api.sportradar.com/"),
    ]
    st.table([{"name": t.name, "url": t.url, "needs_auth": t.needs_auth} for t in targets])

    st.markdown("### Keys (optional)")
    openai_key = _get_secret("OPENAI_API_KEY") or _get_secret("OPENAI_KEY")
    serper_key = _get_secret("SERPER_API_KEY") or _get_secret("SERPER_KEY")
    sportradar_key = _get_secret("SYNERGY_API_KEY") or _get_secret("SPORTRADAR_API_KEY")

    cols = st.columns(3)
    cols[0].write(f"OPENAI key present: `{bool(openai_key)}`")
    cols[1].write(f"SERPER key present: `{bool(serper_key)}`")
    cols[2].write(f"SPORTSRADAR key present: `{bool(sportradar_key)}`")

    timeout_seconds = st.slider("Timeout (seconds)", min_value=2, max_value=30, value=10, step=1)

    if st.button("Run smoke test", type="primary"):
        rows: list[dict[str, str]] = []
        for t in targets:
            rows.append(_probe(t, timeout_seconds, openai_key, serper_key, sportradar_key))
        st.markdown("### Results")
        st.dataframe(rows, use_container_width=True)

        st.info(
            "If you see HTTP status codes (even 401/403/404), egress is working. "
            "If you see timeouts / DNS errors, your network rules or integration attachment is still blocking."
        )


if __name__ == "__main__":
    main()
