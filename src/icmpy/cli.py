from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
from typer import Argument, Context, Exit, Option, Typer

from icmpy import __version__
from icmpy.scaffold import create_workspace
from icmpy.validator import validate_workspace

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
    name: Annotated[str, Argument(help="Name of the workspace directory to create")],
    path: Annotated[
        Path | None,
        Option("--path", help="Directory in which to create the workspace"),
    ] = None,
) -> None:
    """Create a new ICM workspace scaffold."""
    target = (path or Path.cwd()) / name
    dry_run = ctx.obj.get("dry_run", False)
    verbose: int = ctx.obj.get("verbose", 0)

    if dry_run:
        console.print(f"[dry-run] Would create ICM workspace at: {target}")
        return

    create_workspace(target)
    console.print(f"[green]Created ICM workspace:[/green] {target}")

    if verbose:
        console.print("  - CLAUDE.md (Layer 0: workspace identity)")
        console.print("  - CONTEXT.md (Layer 1: workspace routing)")
        console.print("  - _config/voice.md (Layer 3: reference material)")
        console.print("  - stages/ (Layer 2: add numbered stage folders next)")


@app.command()
def validate(
    ctx: Context,
    workspace: Annotated[
        Path | None,
        Option("--workspace", "-w", help="Path to the workspace to validate"),
    ] = None,
) -> None:
    """Validate an ICM workspace structure."""
    workspace_path = workspace or Path.cwd()
    result = validate_workspace(workspace_path)
    if result.ok:
        console.print(f"[green]Workspace is a valid ICM structure:[/green] {workspace_path}")
    else:
        console.print(f"[red]Workspace validation failed:[/red] {workspace_path}")
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)


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
    stage: Annotated[str, Argument(help="Stage number or name to run")],
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
