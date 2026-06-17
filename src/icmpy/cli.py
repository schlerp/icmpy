from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from typer import Argument, Context, Exit, Option, Typer

from icmpy import __version__
from icmpy.builder import (
    TemplateError,
    build_workspace,
    list_templates,
    load_questionnaire,
    load_template_manifest_entry,
    templates_root,
)
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
    from rich.table import Table

    from icmpy.stages import discover_stages

    verbose: int = ctx.obj.get("verbose", 0)
    result = validate_workspace(workspace)
    if not result.ok:
        console.print(f"[red]Invalid workspace:[/red] {workspace}")
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

    stages = discover_stages(workspace)
    if not stages:
        console.print("No numbered stages found.")
        return

    table = Table(title=f"Stages in {workspace}")
    table.add_column("#", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Status")
    if verbose:
        table.add_column("Inputs")
        table.add_column("Outputs")

    for stage in stages:
        row = [f"{stage.number:02d}", stage.name, stage.status]
        if verbose:
            row.append("\n".join(stage.inputs) or "—")
            row.append("\n".join(stage.outputs) or "—")
        table.add_row(*row)

    console.print(table)


@stage_app.command("run")
def stage_run(
    ctx: Context,
    stage: Annotated[
        str | None,
        Argument(help="Stage number or name to run (use 'next' for the first pending stage)"),
    ] = None,
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace"),
    ] = Path.cwd(),
    output: Annotated[
        Path | None,
        Option("--output", "-o", help="File path to write the context bundle to"),
    ] = None,
) -> None:
    """Assemble and run a single stage's context bundle."""
    dry_run = ctx.obj.get("dry_run", False)

    result = validate_workspace(workspace)
    if not result.ok:
        console.print(f"[red]Invalid workspace:[/red] {workspace}")
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

    from icmpy.runner import assemble_context_bundle, render_context_bundle
    from icmpy.stages import find_stage, next_pending_stage

    resolved_stage = stage
    if resolved_stage is None or resolved_stage.lower() == "next":
        pending = next_pending_stage(workspace)
        if pending is None:
            console.print("[green]All stages are complete.[/green]")
            return
        resolved_stage = pending.directory
        console.print(f"[cyan]Next pending stage:[/cyan] {pending.number:02d} {pending.name}")

    if dry_run:
        console.print(f"[dry-run] Would assemble context bundle for stage '{resolved_stage}'")
        return

    try:
        bundle = assemble_context_bundle(workspace, resolved_stage)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    stage_info = find_stage(workspace, resolved_stage)
    if stage_info is None:
        console.print(f"[red]Stage not found:[/red] {resolved_stage}")
        raise Exit(code=1)

    # Warn if the stage inputs are not yet populated
    missing_inputs = []
    for inp in stage_info.inputs:
        if inp.startswith("Layer 4 (working):"):
            rel = inp.split(":", 1)[1].strip().strip("`")
            candidate = stage_info.path / rel
            if not candidate.exists():
                missing_inputs.append(rel)
    if missing_inputs:
        console.print(
            f"[yellow]Note:[/yellow] stage '{stage_info.name}' is missing "
            "expected working artifacts:"
        )
        for missing in missing_inputs:
            console.print(f"  • {missing}")
        console.print("The agent may need you to create these before it can complete the stage.")

    rendered = render_context_bundle(bundle)

    from icmpy.tokens import estimate_tokens

    token_count = estimate_tokens(rendered)
    verbose: int = ctx.obj.get("verbose", 0)
    if token_count > 8000:
        console.print(
            f"[yellow]Warning:[/yellow] estimated context is {token_count} tokens "
            "(recommended upper bound is 8,000)"
        )
    elif verbose:
        console.print(f"Estimated context tokens: {token_count}")

    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"[green]Context bundle written to:[/green] {output}")
    else:
        console.print(rendered)

    # Ensure the stage has an output directory for later human editing
    stage_dir = bundle["stage_dir"]
    (stage_dir / "output").mkdir(exist_ok=True)
    placeholder = stage_dir / "output" / "_ran.txt"
    placeholder.write_text(
        f"Stage '{resolved_stage}' context bundle assembled at runtime.\n"
        "Replace this file with the actual stage outputs.\n",
        encoding="utf-8",
    )


@app.command()
def status(
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace"),
    ] = Path.cwd(),
) -> None:
    """Show a quick health and progress summary for the workspace."""
    from rich.panel import Panel
    from rich.table import Table

    from icmpy.stages import discover_stages, next_pending_stage

    result = validate_workspace(workspace)
    if not result.ok:
        console.print(Panel("[red]Workspace validation failed[/red]", title=str(workspace)))
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

    stages = discover_stages(workspace)
    pending = next_pending_stage(workspace)
    completed = sum(1 for s in stages if s.status == "completed")

    table = Table(title=f"Workspace status: {workspace.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")
    table.add_row("Path", str(workspace))
    table.add_row("Valid", "yes")
    table.add_row("Stages", str(len(stages)))
    table.add_row("Completed", str(completed))
    table.add_row("Pending", str(len(stages) - completed))
    if pending:
        table.add_row("Next stage", f"{pending.number:02d} {pending.name}")
    else:
        table.add_row("Next stage", "[green]all done[/green]")

    console.print(table)


@app.command()
def completion(
    shell: Annotated[
        str,
        Argument(help="Shell to generate completion for: bash, zsh, or fish"),
    ],
) -> None:
    """Print shell completion script for icmp.

    Source it with eval, or redirect to your shell's completion directory.
    """
    import subprocess

    allowed = {"bash", "zsh", "fish"}
    if shell not in allowed:
        console.print(f"[red]Unsupported shell:[/red] {shell}")
        console.print(f"Supported shells: {', '.join(sorted(allowed))}")
        raise Exit(code=1)

    try:
        script = subprocess.check_output(
            ["icmp", f"--install-completion={shell}"],
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]Failed to generate completion:[/red] {exc}")
        raise Exit(code=1) from exc

    console.print(script)


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
    answers_file: Annotated[
        Path | None,
        Option(
            "--answers-file",
            help="JSON file with questionnaire answers (skips interactive prompts)",
        ),
    ] = None,
) -> None:
    """Build a new workspace from a template and questionnaire."""
    dry_run = ctx.obj.get("dry_run", False)
    verbose: int = ctx.obj.get("verbose", 0)

    templates = list_templates()
    if template is None:
        from rich.table import Table

        table = Table(title="Available built-in templates")
        table.add_column("Template", style="cyan")
        table.add_column("Pipeline")
        for entry in templates:
            table.add_row(entry["name"], entry["description"])
        console.print(table)
        console.print("\nUse [bold]icmp build --template <name>[/bold] to select one.")
        raise Exit(code=1)

    try:
        manifest = load_template_manifest_entry(template)
        template_dir = templates_root() / manifest["path"]
        questionnaire = load_questionnaire(template_dir)
    except TemplateError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    if dry_run:
        console.print(f"[dry-run] Would build workspace from template '{template}' into {target}")
        return

    if answers_file:
        import json

        if not answers_file.is_file():
            console.print(f"[red]Answers file not found:[/red] {answers_file}")
            raise Exit(code=1)
        try:
            answers: dict[str, Any] = json.loads(answers_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            console.print(f"[red]Invalid JSON in answers file:[/red] {exc}")
            raise Exit(code=1) from exc
    else:
        answers = {}
        for item in questionnaire:
            key = item["key"]
            question = item["question"]
            default = item.get("default", "")
            qtype = item.get("type", "text")
            if qtype == "integer":
                value = str(
                    typer.prompt(question, default=int(default) if default else 0, type=int)
                )
            elif qtype == "confirm":
                value = "yes" if typer.confirm(question, default=bool(default)) else "no"
            else:
                value = typer.prompt(question, default=default)
            answers[key] = value

    try:
        workspace_path = build_workspace(template, target, answers, validate=True)
    except (FileExistsError, TemplateError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    console.print(f"[green]Built workspace:[/green] {workspace_path}")
    if verbose:
        console.print(f"Using template '{template}' with {len(answers)} answers")
