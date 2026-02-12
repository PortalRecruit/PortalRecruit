import os
import re
import requests

SERPER_ENDPOINTS = {
    "search": "https://google.serper.dev/search",
    "images": "https://google.serper.dev/images",
    "videos": "https://google.serper.dev/videos",
}


def serper_search(query: str, type: str = "search", num: int = 6) -> list[dict]:
    api_key = os.getenv("SERPER_API_KEY") or os.getenv("SERPER_KEY")
    if not api_key:
        return []
    endpoint = SERPER_ENDPOINTS.get(type, SERPER_ENDPOINTS["search"])
    try:
        resp = requests.post(
            endpoint,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        key = "images" if type == "images" else "videos" if type == "videos" else "organic"
        return data.get(key, []) or []
    except Exception:
        return []


def _openai_chat(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a precise selector. Return only the requested ID or URL."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 80,
            },
            timeout=25,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def select_best_video(video_results: list[dict], player_name: str) -> str | None:
    if not video_results:
        return None
    urls = []
    for r in video_results:
        link = r.get("link") or r.get("url") or ""
        if "youtube.com" in link or "youtu.be" in link:
            urls.append(link)
    if not urls:
        return None

    prompt = (
        f"Given these search results, identify the video ID that is most likely a highlight reel or full game tape for {player_name}. "
        "Exclude interviews or podcasts. Return only the YouTube ID.\n\n" + "\n".join(urls)
    )
    content = _openai_chat(prompt)
    if content:
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", content)
        if m:
            return m.group(1)
        if re.fullmatch(r"[A-Za-z0-9_-]{6,}", content):
            return content
    # fallback: first URL
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", urls[0])
    return m.group(1) if m else None


def select_best_image(image_results: list[dict], player_name: str) -> str | None:
    if not image_results:
        return None
    urls = [r.get("imageUrl") or r.get("link") or r.get("url") for r in image_results]
    urls = [u for u in urls if u]
    if not urls:
        return None

    prompt = (
        f"Pick the single image URL most likely to show {player_name} in a jersey or on a court. "
        "Avoid logos or text graphics. Return only the URL.\n\n" + "\n".join(urls[:12])
    )
    content = _openai_chat(prompt)
    if content and content.startswith("http"):
        return content
    return urls[0]


def build_video_query(player_name: str, team_name: str) -> str:
    return f'site:youtube.com "{player_name}" "{team_name}" basketball -intitle:shorts'


def build_image_query(player_name: str, team_name: str) -> str:
    return f'"{player_name}" "{team_name}" basketball game photo -card -ebay -jersey'
