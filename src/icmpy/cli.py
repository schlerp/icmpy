from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
from typer import Context, Exit, Option, Typer

from icmpy import __version__

console = Console()

app = Typer(
    name="icmp",
    help="Interpretable Context Methodology (ICM) scaffolding tool",
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"icmpy {__version__}")
        raise Exit(code=0)


@app.callback()
def main(
    ctx: Context,
    version: Annotated[
        bool,
        Option("--version", "-v", callback=_version_callback, is_eager=True, help="Show version"),
    ] = False,
    dry_run: Annotated[
        bool,
        Option("--dry-run", help="Show what would happen without making changes"),
    ] = False,
    verbose: Annotated[
        int,
        Option("--verbose", "-V", count=True, help="Increase verbosity"),
    ] = 0,
) -> None:
    """icmp: scaffolding and orchestration for ICM workspaces."""
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose


@app.command()
def init(
    ctx: Context,
    name: Annotated[str, "Name of the workspace directory to create"],
    path: Annotated[
        Path | None,
        Option("--path", help="Directory in which to create the workspace"),
    ] = None,
) -> None:
    """Create a new ICM workspace scaffold."""
    target = (path or Path.cwd()) / name
    dry_run = ctx.obj.get("dry_run", False)
    verbose = ctx.obj.get("verbose", 0)
    console.print(f"[bold]icmp init[/bold] {name}")
    if dry_run:
        console.print(f"Would create workspace at {target}")
        return

    # Placeholder for scaffold logic
    target.mkdir(parents=True, exist_ok=True)
    console.print(f"Created workspace at {target}")
    if verbose:
        console.print("Layer 0 (CLAUDE.md) and Layer 1 (CONTEXT.md) scaffolds written.")


@app.command()
def validate(
    ctx: Context,
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace to validate"),
    ] = Path.cwd(),
) -> None:
    """Validate an ICM workspace structure."""
    console.print(f"[bold]icmp validate[/bold] {workspace}")


stage_app = Typer(
    name="stage",
    help="Work with ICM stages",
    no_args_is_help=True,
)
app.add_typer(stage_app)


@stage_app.command("list")
def stage_list(
    ctx: Context,
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace"),
    ] = Path.cwd(),
) -> None:
    """List stages in the current workspace."""
    console.print(f"[bold]icmp stage list[/bold] {workspace}")


@stage_app.command("run")
def stage_run(
    ctx: Context,
    stage: Annotated[str, "Stage number or name to run"],
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace"),
    ] = Path.cwd(),
) -> None:
    """Assemble and run a single stage's context bundle."""
    console.print(f"[bold]icmp stage run[/bold] {stage} in {workspace}")


@app.command()
def build(
    ctx: Context,
    template: Annotated[
        str | None,
        Option("--template", "-t", help="Built-in template name"),
    ] = None,
    target: Annotated[
        Path,
        Option("--target", help="Directory in which to build the workspace"),
    ] = Path.cwd(),
) -> None:
    """Build a new workspace from a template and questionnaire."""
    console.print(f"[bold]icmp build[/bold] template={template} target={target}")
