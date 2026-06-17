from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from icmpy.cli import app
from icmpy.runner import assemble_context_bundle, render_context_bundle
from icmpy.scaffold import create_workspace

runner = CliRunner()


def _write_valid_workspace(path: Path) -> None:
    create_workspace(path)
    research = path / "stages" / "01_research"
    research.mkdir()
    topic_brief = research / "output" / "topic_brief.md"
    topic_brief.parent.mkdir(parents=True)
    topic_brief.write_text("Topic: AI Safety")
    (research / "CONTEXT.md").write_text(
        "# Research\n\n## Inputs\n\n"
        "- Layer 4 (working): `output/topic_brief.md`\n"
        "- Layer 3 (reference): `_config/voice.md`\n\n"
        "## Process\n\nAnalyze.\n\n## Outputs\n\n- summary.md\n"
    )


def test_assemble_context_bundle(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    bundle = assemble_context_bundle(tmp_path, "01")
    assert "Research" in bundle["stage_name"]
    assert bundle["layer_0_identity"]
    assert bundle["layer_1_routing"]
    assert bundle["layer_2_contract"]
    assert any("topic_brief.md" in p for p, _ in bundle["layer_4_working"])
    assert any("voice.md" in p for p, _ in bundle["layer_3_reference"])


def test_render_context_bundle_includes_layers(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    bundle = assemble_context_bundle(tmp_path, "01")
    rendered = render_context_bundle(bundle)
    assert "Layer 0" in rendered
    assert "Layer 1" in rendered
    assert "Layer 2" in rendered
    assert "Layer 3" in rendered
    assert "Layer 4" in rendered
    assert "topic_brief.md" in rendered


def test_cli_stage_run_outputs_bundle(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    result = runner.invoke(app, ["stage", "run", "01", "--workspace", str(tmp_path)])
    assert result.exit_code == 0
    assert "Layer 0" in result.output
    assert "topic_brief.md" in result.output
    assert (tmp_path / "stages" / "01_research" / "output" / "_ran.txt").is_file()


def test_cli_stage_run_writes_output_file(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    output_path = tmp_path / "bundle.md"
    result = runner.invoke(
        app, ["stage", "run", "01", "--workspace", str(tmp_path), "--output", str(output_path)]
    )
    assert result.exit_code == 0
    assert output_path.is_file()
    assert "Layer 0" in output_path.read_text()


def test_cli_stage_run_unknown_stage(tmp_path: Path) -> None:
    _write_valid_workspace(tmp_path)
    result = runner.invoke(app, ["stage", "run", "99", "--workspace", str(tmp_path)])
    assert result.exit_code == 1
    assert "Stage not found" in result.output


def test_cli_stage_run_invalid_workspace(tmp_path: Path) -> None:
    result = runner.invoke(app, ["stage", "run", "01", "--workspace", str(tmp_path / "nowhere")])
    assert result.exit_code == 1
    assert "Invalid workspace" in result.output
