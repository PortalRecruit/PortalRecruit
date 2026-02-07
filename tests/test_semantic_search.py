from src.search.semantic import semantic_search


class DummyCollection:
    def query(self, **kwargs):
        return {
            "ids": [["p1", "p2", "p3"]],
            "documents": [[
                "high motor wing gets deflections and loose balls",
                "spot up shooter and catch and shoot scoring",
                "rim protection and blocks in drop coverage",
            ]],
            "distances": [[0.25, 0.15, 0.35]],
            "metadatas": [[
                {"tags": "deflection,loose_ball,wing"},
                {"tags": "3pt,jumpshot"},
                {"tags": "block,rim_protection"},
            ]],
        }


def test_semantic_search_fallback_without_cross_encoder(monkeypatch):
    def boom():
        raise RuntimeError("no model")

    monkeypatch.setattr("src.search.semantic.get_cross_encoder", boom)
    monkeypatch.setattr("src.search.semantic.encode_query", lambda q: [0.1, 0.2, 0.3])
    results = semantic_search(
        DummyCollection(),
        query="high motor wing deflections",
        n_results=2,
        required_tags=["deflection"],
    )
    assert len(results) == 2
    assert results[0] == "p1"


def test_semantic_search_uses_rerank(monkeypatch):
    class DummyCross:
        def predict(self, pairs, batch_size=16):
            mapping = {
                "high motor wing gets deflections and loose balls": 0.2,
                "spot up shooter and catch and shoot scoring": 0.1,
                "rim protection and blocks in drop coverage": 1.0,
            }
            return [mapping[p[1]] for p in pairs]

    monkeypatch.setattr("src.search.semantic.get_cross_encoder", lambda: DummyCross())
    monkeypatch.setattr("src.search.semantic.encode_query", lambda q: [0.1, 0.2, 0.3])
    results = semantic_search(
        DummyCollection(),
        query="drop coverage rim protector",
        n_results=2,
        required_tags=["block", "rim_protection"],
    )
    assert results[0] == "p3"
