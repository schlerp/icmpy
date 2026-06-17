from __future__ import annotations

import pytest

from icmpy.models import StageContract, StageInput, WorkspaceConfig


def test_stage_input_requires_relative_path() -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        StageInput(layer=3, path="/absolute/path.md")


def test_stage_contract_creation() -> None:
    contract = StageContract(
        name="Research",
        directory="01_research",
        inputs=[StageInput(layer=4, path="output/source_material.md")],
        process="Analyze the source material and produce a research summary.",
        outputs=["research_summary.md"],
    )
    assert contract.name == "Research"
    assert contract.directory == "01_research"
    assert len(contract.inputs) == 1
    assert contract.outputs == ["research_summary.md"]


def test_workspace_config_unique_directories() -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        WorkspaceConfig(
            name="test",
            stages=[
                StageContract(name="A", directory="01_a", process="do a"),
                StageContract(name="B", directory="01_a", process="do b"),
            ],
        )
