import argparse
import csv

from src.position_calibration import calibrate_all, export_model_bundle, learn_global_weights_logreg

POSITION_MAP = {
    "G": "GUARD",
    "F": "FORWARD",
    "C": "CENTER",
    "F/C": "CENTER",
    "G/F": "SMALL_FORWARD",
    "PG": "POINT_GUARD",
    "SG": "SHOOTING_GUARD",
    "SF": "SMALL_FORWARD",
    "PF": "POWER_FORWARD",
}


def load_samples(path: str):
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_pos = (row.get("true_position") or "").strip()
            pos = POSITION_MAP.get(raw_pos, raw_pos)
            samples.append(
                {
                    "true_position": pos,
                    "height_in": float(row.get("height_in") or 0.0) if row.get("height_in") else None,
                    "weight_lb": float(row.get("weight_lb") or 0.0) if row.get("weight_lb") else None,
                    "text": row.get("text") or "",
                }
            )
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/calibration_samples.csv")
    parser.add_argument("--min-group-hits", type=int, default=40)
    args = parser.parse_args()

    samples = load_samples(args.data)
    cal = calibrate_all(samples, min_group_hits=args.min_group_hits)
    pos_candidates = sorted({s["true_position"] for s in samples if s.get("true_position")})
    weights = learn_global_weights_logreg(samples, candidate_positions=pos_candidates)
    export_model_bundle(
        "position_model.json",
        cal["priors"],
        cal["group_size_updates"],
        weights,
    )


if __name__ == "__main__":
    main()
