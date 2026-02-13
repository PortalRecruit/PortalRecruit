from __future__ import annotations

from typing import List, Tuple, Dict, Any


def generate_pca_coordinates(embeddings_list: List[List[float]]) -> List[Tuple[float, float]]:
    try:
        if embeddings_list is None or len(embeddings_list) == 0:
            return []
    except Exception:
        return []
    try:
        from sklearn.decomposition import PCA
        import numpy as np

        X = np.array(embeddings_list)
        pca = PCA(n_components=2)
        coords = pca.fit_transform(X)
        return [(float(x), float(y)) for x, y in coords]
    except Exception:
        return [(0.0, 0.0) for _ in embeddings_list]


def generate_radar_chart(player_a: Dict[str, Any], player_b: Dict[str, Any], query: str = "Big Guard"):
    import plotly.graph_objects as go
    from src.position_calibration import calculate_percentile, map_db_to_canonical, score_positions, topk

    def _pos_for(player):
        pos = player.get("position") or ""
        mapped = map_db_to_canonical(pos)
        return mapped[0] if mapped else pos

    def _fit_score(player):
        h = player.get("height_in")
        w = player.get("weight_lb")
        scores = score_positions(query, height_in=h, weight_lb=w)
        top = topk(scores, k=1)
        if not top:
            return 0.0
        max_score = max(scores.values()) or 1.0
        return max(0.0, min(1.0, top[0][1] / max_score)) * 100.0

    def _overall(player):
        val = player.get("score") or player.get("Recruit Score") or 0.0
        try:
            val = float(val)
        except Exception:
            val = 0.0
        return max(0.0, min(100.0, val))

    pos_a = _pos_for(player_a)
    pos_b = _pos_for(player_b)
    h_pct_a = calculate_percentile(player_a.get("height_in"), pos_a, metric="h")
    w_pct_a = calculate_percentile(player_a.get("weight_lb"), pos_a, metric="w")
    h_pct_b = calculate_percentile(player_b.get("height_in"), pos_b, metric="h")
    w_pct_b = calculate_percentile(player_b.get("weight_lb"), pos_b, metric="w")

    categories = ["Height %", "Weight %", "Vector Match", "Scout Score"]
    a_vals = [h_pct_a, w_pct_a, _fit_score(player_a), _overall(player_a)]
    b_vals = [h_pct_b, w_pct_b, _fit_score(player_b), _overall(player_b)]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=a_vals, theta=categories, fill="toself", name=player_a.get("name", "Player A"), line=dict(color="#31d0ff")))
    fig.add_trace(go.Scatterpolar(r=b_vals, theta=categories, fill="toself", name=player_b.get("name", "Player B"), line=dict(color="#7f8ba3")))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#f3f6ff"),
    )
    return fig
