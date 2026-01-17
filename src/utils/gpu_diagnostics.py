# ================================
# File: src/utils/gpu_diagnostics.py
# ================================
"""
GPU diagnostics utility.
Run directly or import assert_cuda_ready().
"""

import subprocess
import torch


def assert_cuda_ready() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")

    _ = torch.empty((1,), device="cuda")
    torch.cuda.synchronize()


def print_diagnostics() -> None:
    print("=== GPU DIAGNOSTICS ===")
    print(f"Torch Version: {torch.__version__}")
    print(f"Torch CUDA: {torch.version.cuda}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    try:
        out = subprocess.check_output(
            ["ffmpeg", "-hwaccels"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        print("FFmpeg HW Accels:")
        print(out.strip())
    except Exception:
        print("FFmpeg not found or no hwaccels available")

    print("=======================")


if __name__ == "__main__":
    assert_cuda_ready()
    print_diagnostics()


# =================================
# File: src/ingestion/ingest_game.py
# =================================
"""
High-throughput ingestion with GPU batching + async FFmpeg.
"""

import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

import chromadb
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.ingestion.synergy_client import SynergyClient
from src.processing.vibe_check import get_image_embedding
from src.utils.gpu_diagnostics import assert_cuda_ready


LEAGUE = "ncaamb"
TARGET_TEAM = "Texas A&M"
TARGET_EVENTS = ["Dunk", "Steal", "Block", "3pt", "Technical Foul"]

MAX_FRAMES = 15
BATCH_SIZE = 8
FFMPEG_WORKERS = 4


def ffmpeg_extract_frame(video_url: str, offset: int, output_path: str) -> bool:
    cmd = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-ss", str(offset),
        "-i", video_url,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        output_path,
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def calculate_video_offset(period: int, clock: str, period_length: int = 20) -> int:
    mins, secs = map(int, clock.split(":"))
    elapsed = (period_length * 60) - (mins * 60 + secs)
    if period == 2:
        elapsed += (20 * 60) + 120
    return elapsed


def batch(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def run_ingestion() -> None:
    assert_cuda_ready()
    device = "cuda"
    print("⚙ Hardware Acceleration: CUDA (NVIDIA Enabled)")

    client = SynergyClient()

    db_path = os.path.join(os.getcwd(), "data/vector_db")
    chroma = chromadb.PersistentClient(path=db_path)
    collection = chroma.get_or_create_collection("skout_plays")

    seasons = client.get_seasons(LEAGUE)
    seasons = [w["data"] for w in seasons["data"] if "data" in w]
    seasons.sort(key=lambda s: s["name"], reverse=True)
    season = seasons[0]

    teams = client.get_teams(LEAGUE, season["id"])
    team_id = None
    for w in teams["data"]:
        t = w.get("data")
        if t and TARGET_TEAM.lower() in t["name"].lower():
            team_id = t["id"]
            break

    games = client.get_games(LEAGUE, season["id"], team_id=team_id, limit=20)
    games = [w["data"] for w in games["data"] if "data" in w]
    game = next(g for g in games if g.get("playlistUrl"))

    events = client.get_game_events(LEAGUE, game["id"])
    events = [w["data"] for w in events["data"] if "data" in w]

    tasks: List[Tuple[str, str, str]] = []
    for idx, e in enumerate(events):
        if len(tasks) >= MAX_FRAMES:
            break
        desc = e.get("description", "")
        if not any(x in desc for x in TARGET_EVENTS):
            continue
        if ":" not in str(e.get("clock")):
            continue

        play_id = f"{game['id']}_{e['clock'].replace(':','')}_{idx}"
        out_path = f"data/video_clips/{play_id}.jpg"
        if os.path.exists(out_path):
            continue

        offset = calculate_video_offset(e["period"], e["clock"])
        tasks.append((play_id, offset, out_path))

    extracted = []
    with ThreadPoolExecutor(max_workers=FFMPEG_WORKERS) as pool:
        futures = {
            pool.submit(
                ffmpeg_extract_frame,
                game["playlistUrl"],
                offset,
                path,
            ): (pid, path)
            for pid, offset, path in tasks
        }

        for f in as_completed(futures):
            pid, path = futures[f]
            if f.result():
                extracted.append((pid, path))

    print(f"🎥 Extracted {len(extracted)} frames")

    for chunk in batch(extracted, BATCH_SIZE):
        ids, paths = zip(*chunk)
        vectors = [get_image_embedding(p) for p in paths]

        collection.add(
            ids=list(ids),
            embeddings=vectors,
            metadatas=[
                {
                    "filepath": p,
                    "game": f"{game['awayTeam']['abbr']} vs {game['homeTeam']['abbr']}",
                }
                for p in paths
            ],
        )

    print("🎉 Ingestion complete")


if __name__ == "__main__":
    run_ingestion()
