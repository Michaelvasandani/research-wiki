from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app
from test_atomic_paper_ingest import text_pdf


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(data_dir: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                codex_command=(sys.executable, str(FAKE_CODEX)),
                run_ingest_service=False,
            )
        )
    )


def publish_paper(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/sources",
        files={"file": (filename, text_pdf(text), "application/pdf")},
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def test_graph_api_exposes_published_page_identity_type_target_and_explicit_edges(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_source = publish_paper(client, "first.pdf", "A research method is evaluated.")
        second_source = publish_paper(client, "second.pdf", "A related research method is evaluated.")
        graph = client.get("/api/graph")

    assert graph.status_code == 200
    payload = graph.json()
    nodes = {node["target"]: node for node in payload["nodes"]}
    assert nodes[f"/wiki/papers/{first_source}"] == {
        "id": f"paper-{first_source}",
        "title": "first",
        "type": "paper",
        "target": f"/wiki/papers/{first_source}",
        "connections": 1,
        "color": "#2d6a9f",
    }
    assert nodes["/wiki/topics/research-methods"] == {
        "id": "topic-research-methods",
        "title": "Research methods",
        "type": "topic",
        "target": "/wiki/topics/research-methods",
        "connections": 2,
        "color": "#3d8b67",
    }
    assert {
        (edge["source"], edge["target"])
        for edge in payload["edges"]
    } == {
        (f"paper-{first_source}", "topic-research-methods"),
        (f"paper-{second_source}", "topic-research-methods"),
    }
    assert payload["validation"] == []


def test_graph_excludes_invalid_wikilink_targets_and_exposes_validation_from_published_snapshot(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = publish_paper(client, "paper.pdf", "A research method is evaluated.")
        paper_path = tmp_path / "vault" / "papers" / f"{source_id}.md"
        paper_path.write_text(
            paper_path.read_text(encoding="utf-8").replace(
                "[[topics/research-methods|Research methods]]",
                "[[topics/missing-method|Missing method]]",
            ),
            encoding="utf-8",
        )
        graph = client.get("/api/graph")

    assert graph.status_code == 200
    payload = graph.json()
    assert all("missing-method" not in edge["target"] for edge in payload["edges"])
    assert all(node["target"] != "/wiki/topics/missing-method" for node in payload["nodes"])
    assert payload["validation"] == [
        {
            "source": f"paper-{source_id}",
            "target": "topics/missing-method",
            "message": "Explicit wikilink target is not a published wiki page.",
        }
    ]


def test_graph_distinguishes_a_filed_analysis_from_papers_and_topics(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        source_id = publish_paper(client, "paper.pdf", "A research method is evaluated.")
        analysis = tmp_path / "vault" / "analyses" / "method-synthesis.md"
        analysis.parent.mkdir()
        analysis.write_text(
            "---\n"
            "page_type: filed-analysis\n"
            "id: analysis-method-synthesis\n"
            "title: \"Method synthesis\"\n"
            "---\n"
            "[[papers/" + source_id + "]]\n",
            encoding="utf-8",
        )
        graph = client.get("/api/graph")

    nodes = {node["id"]: node for node in graph.json()["nodes"]}
    assert nodes["analysis-method-synthesis"] == {
        "id": "analysis-method-synthesis",
        "title": "Method synthesis",
        "type": "filed-analysis",
        "target": "/wiki/analyses/method-synthesis",
        "connections": 1,
        "color": "#9b5b8f",
    }


def test_graph_page_uses_d3_for_pan_zoom_hover_labels_and_click_navigation(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        source_id = publish_paper(client, "paper.pdf", "A research method is evaluated.")
        graph = client.get("/graph")

    assert graph.status_code == 200
    assert 'id="knowledge-graph"' in graph.text
    assert 'src="/assets/d3.v7.9.0.min.js"' in graph.text
    asset = client.get("/assets/d3.v7.9.0.min.js")
    assert asset.status_code == 200
    assert "forceSimulation" in asset.text
    assert 'fetch("/api/graph")' in graph.text
    assert "d3.forceSimulation" in graph.text
    assert "d3.zoom" in graph.text
    assert "pointerenter" in graph.text
    assert "window.location.assign(node.target)" in graph.text
    assert f"/wiki/papers/{source_id}" not in graph.text
