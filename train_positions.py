import csv

from src.position_calibration import calibrate_all, export_model_bundle

POSITION_MAP = {
    "G": "GUARD",
    "F": "FORWARD",
    "C": "CENTER",
    "F/C": "CENTER",
    "G/F": "SMALL_FORWARD",
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
    samples = load_samples("data/calibration_samples.csv")
    cal = calibrate_all(samples, min_group_hits=0)
    export_model_bundle(
        "position_model.json",
        cal["priors"],
        cal["group_size_updates"],
        cal["weights"],
    )


if __name__ == "__main__":
    main()
