from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ContextLayer(IntEnum):
    """The five-layer ICM context hierarchy."""

    WORKSPACE_IDENTITY = 0
    WORKSPACE_ROUTING = 1
    STAGE_CONTRACT = 2
    REFERENCE_MATERIAL = 3
    WORKING_ARTIFACTS = 4


class ContentLayerKind(str):
    """Discriminator for Layer 3 vs Layer 4 content."""

    REFERENCE = "reference"
    WORKING = "working"


class StageInput(BaseModel):
    """A single input declared in a stage contract."""

    layer: Literal[3, 4] = Field(description="ICM layer for this input: 3 reference, 4 working")
    path: str = Field(description="Path relative to the workspace root or stage folder")
    sections: list[str] | None = Field(
        default=None,
        description="Optional list of sections within the file to load",
    )

    @field_validator("path")
    @classmethod
    def _path_must_be_relative(cls, value: str) -> str:
        if Path(value).is_absolute():
            msg = "Stage input paths must be relative"
            raise ValueError(msg)
        return value


class StageContract(BaseModel):
    """The Layer 2 contract for one stage of an ICM pipeline."""

    name: str = Field(description="Human-readable stage name")
    directory: str = Field(description="Directory name, e.g. '01_research'")
    inputs: list[StageInput] = Field(default_factory=list)
    process: str = Field(description="Instructions for what the agent does at this stage")
    outputs: list[str] = Field(
        default_factory=list,
        description="Relative paths this stage writes to its output folder",
    )
    verify: list[str] | None = Field(
        default=None,
        description="Optional cross-stage verification checks",
    )


class WorkspaceConfig(BaseModel):
    """Top-level parsed configuration for an ICM workspace."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    stages: list[StageContract] = Field(default_factory=list)

    @field_validator("stages")
    @classmethod
    def _stages_must_have_unique_directories(
        cls, stages: list[StageContract]
    ) -> list[StageContract]:
        directories = [stage.directory for stage in stages]
        if len(directories) != len(set(directories)):
            msg = "Stage directories must be unique"
            raise ValueError(msg)
        return stages


def build_layer_summary(layer: ContextLayer, content: dict[str, Any]) -> str:
    """Summarize a loaded context layer for inclusion in a bundle heading."""
    return f"=== Layer {int(layer)}: {layer.name.replace('_', ' ').title()} ==="
