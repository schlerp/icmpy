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
    copy_builtin_to_custom,
    discover_templates,
    resolve_template,
    template_info,
    validate_template,
)
from icmpy.harness import HarnessError, list_harnesses, run_harness
from icmpy.scaffold import create_workspace
from icmpy.template_catalog import get_custom_template_root
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
    harness: Annotated[
        str | None,
        Option("--harness", help="Dispatch the bundle to an LLM harness instead of printing it"),
    ] = None,
) -> None:
    """Assemble and run a single stage's context bundle."""
    dry_run = ctx.obj.get("dry_run", False)
    verbose: int = ctx.obj.get("verbose", 0)

    result = validate_workspace(workspace)
    if not result.ok:
        console.print(f"[red]Invalid workspace:[/red] {workspace}")
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

    from icmpy.runner import assemble_context_bundle, render_context_bundle
    from icmpy.stages import RUN_FLAG, find_stage, next_pending_stage

    resolved_stage = stage
    if resolved_stage is None or resolved_stage.lower() == "next":
        pending = next_pending_stage(workspace)
        if pending is None:
            console.print("[green]All stages are complete.[/green]")
            return
        resolved_stage = pending.directory
        console.print(f"[cyan]Next pending stage:[/cyan] {pending.number:02d} {pending.name}")

    if dry_run and not harness:
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

    stage_dir = bundle["stage_dir"]
    output_dir = stage_dir / "output"
    output_dir.mkdir(exist_ok=True)

    if harness:
        harness = harness.lower()
        try:
            response, command = run_harness(
                harness,
                rendered,
                workspace_path=workspace,
                stage_dir=stage_dir,
                dry_run=dry_run,
            )
        except HarnessError as exc:
            console.print(f"[red]Harness error:[/red] {exc}")
            raise Exit(code=1) from exc

        if dry_run:
            console.print(response)
            return

        harness_output = output_dir / f"{harness}.md"
        harness_output.write_text(response, encoding="utf-8")
        run_flag = output_dir / RUN_FLAG
        run_flag.write_text(
            f"Stage '{resolved_stage}' dispatched to harness '{harness}'.\n"
            f"Command: {' '.join(command)}\n"
            f"Response saved to: {harness_output.name}\n",
            encoding="utf-8",
        )
        console.print(f"[green]Dispatched to harness:[/green] {harness}")
        console.print(f"[green]Response written to:[/green] {harness_output}")
        if verbose:
            console.print(f"Command: {' '.join(command)}")
        return

    if not output:
        console.print(rendered)

    # Ensure the stage has an output directory for later human editing
    placeholder = output_dir / RUN_FLAG
    placeholder.write_text(
        f"Stage '{resolved_stage}' context bundle assembled at runtime.\n"
        "Replace this file with the actual stage outputs.\n",
        encoding="utf-8",
    )


harness_app = Typer(
    name="harness",
    help="Dispatch stages to LLM harnesses",
    no_args_is_help=True,
)
app.add_typer(harness_app)


@harness_app.command("list")
def harness_list() -> None:
    """List available LLM harness adapters."""
    names = list_harnesses()
    if not names:
        console.print("No harness adapters configured.")
        return
    console.print("Available harnesses:")
    for name in names:
        console.print(f"  • {name}")


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
def reset(
    ctx: Context,
    stage: Annotated[
        str | None,
        Argument(help="Stage number or name to reset (omit to reset all stages)"),
    ] = None,
    workspace: Annotated[
        Path,
        Option("--workspace", "-w", help="Path to the workspace"),
    ] = Path.cwd(),
    remove_outputs: Annotated[
        bool,
        Option("--remove-outputs", help="Also remove all files in each stage's output directory"),
    ] = False,
) -> None:
    """Remove the run flag for a stage (or all stages), optionally deleting outputs."""
    dry_run = ctx.obj.get("dry_run", False)

    result = validate_workspace(workspace)
    if not result.ok:
        console.print(f"[red]Invalid workspace:[/red] {workspace}")
        for error in result.errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

    from icmpy.stages import clear_stage, discover_stages, find_stage

    if stage is None:
        target_stages = discover_stages(workspace)
    else:
        resolved = find_stage(workspace, stage)
        if resolved is None:
            console.print(f"[red]Stage not found:[/red] {stage}")
            raise Exit(code=1)
        target_stages = [resolved]

    if not target_stages:
        console.print("No stages to reset.")
        return

    prefix = "dry-run: " if dry_run else ""
    total = 0
    for stage_info in target_stages:
        removed = clear_stage(stage_info, remove_outputs=remove_outputs, dry_run=dry_run)
        if not removed:
            console.print(
                f"{prefix}No run flag to clear for stage {stage_info.number:02d} {stage_info.name}"
            )
            continue
        total += len(removed)
        if remove_outputs:
            console.print(
                f"{prefix}Removed outputs for stage {stage_info.number:02d} {stage_info.name}"
            )
        else:
            console.print(
                f"{prefix}Cleared run flag for stage {stage_info.number:02d} {stage_info.name}"
            )
        verbose: int = ctx.obj.get("verbose", 0)
        if verbose or dry_run:
            for path in removed:
                console.print(f"  • {path.relative_to(workspace)}")

    if stage is None:
        noun = "output directory" if remove_outputs else "run flag"
        label = "would affect" if dry_run else "removed"
        console.print(f"{prefix}Reset {len(target_stages)} stage(s) ({label} {total} {noun}(s)).")


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


build_app = Typer(
    name="build",
    help="Build workspaces from templates",
    no_args_is_help=True,
)
app.add_typer(build_app)


@build_app.command("list")
def build_list() -> None:
    """List available built-in and custom templates."""
    from rich.table import Table

    templates = discover_templates()
    if not templates:
        console.print("No templates found.")
        return

    table = Table(title="Available templates")
    table.add_column("Template", style="cyan")
    table.add_column("Origin")
    table.add_column("Pipeline")
    for entry in templates:
        table.add_row(
            entry["name"],
            entry["origin"],
            entry["description"],
        )
    console.print(table)


@build_app.command("info")
def build_info(
    template: Annotated[str, Argument(help="Template name")],
    origin: Annotated[
        str | None,
        Option("--origin", help="Origin filter: built-in or custom"),
    ] = None,
) -> None:
    """Show details about a template: description, questions, and stages."""
    from rich.table import Table

    try:
        info = template_info(template, origin=origin)
    except TemplateError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    console.print(f"[cyan]{info['name']}[/cyan] ({info['origin']}): {info['description']}")

    if info["questions"]:
        table = Table(title="Questions")
        table.add_column("Key", style="cyan")
        table.add_column("Type")
        table.add_column("Default")
        for q in info["questions"]:
            table.add_row(q["key"], q["type"], str(q["default"]))
        console.print(table)

    if info["stages"]:
        table = Table(title="Stages")
        table.add_column("#", justify="right", style="cyan")
        table.add_column("Name")
        for stage in info["stages"]:
            number = stage["directory"].split("_", 1)[0]
            table.add_row(number, stage["name"])
        console.print(table)


@build_app.command("create")
def build_create(
    ctx: Context,
    template: Annotated[
        str | None,
        Option("--template", "-t", help="Template name"),
    ] = None,
    origin: Annotated[
        str | None,
        Option("--origin", help="Origin filter: built-in or custom"),
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

    if template is None:
        console.print("[yellow]No template selected.[/yellow]")
        console.print(
            "Choose one with [bold]icmp build list[/bold] or pass [bold]--template[/bold]."
        )
        raise Exit(code=1)

    try:
        template_entry = resolve_template(template, origin=origin)
        template_dir = template_entry["path"]
        questionnaire = load_questionnaire(template_dir)
    except TemplateError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    validation_errors = validate_template(template, answers=None, origin=origin)
    if validation_errors:
        console.print(f"[red]Template '{template}' failed validation:[/red]")
        for error in validation_errors:
            console.print(f"  • {error}")
        raise Exit(code=1)

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
        workspace_path = build_workspace(template, target, answers, validate=True, origin=origin)
    except (FileExistsError, TemplateError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc

    console.print(f"[green]Built workspace:[/green] {workspace_path}")
    if verbose:
        console.print(f"Using template '{template}' with {len(answers)} answers")


def load_questionnaire(template_dir: Path) -> list[dict[str, Any]]:
    """Load the questionnaire for a template directory."""
    from icmpy.builder import load_questionnaire as _load_questionnaire

    return _load_questionnaire(template_dir)


template_app = Typer(
    name="template",
    help="Manage workspace templates",
    no_args_is_help=True,
)
app.add_typer(template_app)


@template_app.command("path")
def template_path(
    create: Annotated[
        bool,
        Option("--create", help="Create the custom template directory if it does not exist"),
    ] = False,
) -> None:
    """Print the custom template directory path."""
    root = get_custom_template_root()
    if create and not root.is_dir():
        root.mkdir(parents=True, exist_ok=True)
    console.print(str(root), soft_wrap=True)


@template_app.command("list")
def template_list() -> None:
    """List built-in and custom templates, noting name collisions."""
    from rich.table import Table

    from icmpy.template_catalog import TemplateCatalog, TemplateOrigin

    catalog = TemplateCatalog()
    templates = catalog.templates

    if not templates:
        console.print("No templates found.")
        return

    table = Table(title="Available templates")
    table.add_column("Template", style="cyan")
    table.add_column("Origin")
    table.add_column("Description")
    table.add_column("Note")

    for template in templates:
        note = ""
        if catalog.is_shadowed(template):
            if template.origin == TemplateOrigin.CUSTOM:
                note = "shadows built-in"
            else:
                note = "shadowed"
        table.add_row(
            template.name,
            template.origin.value,
            template.description,
            note,
        )

    console.print(table)

    if not catalog.custom_root.is_dir():
        console.print(
            "No custom templates directory found. Run `icmp template path` "
            "to see where to create one."
        )

    for warning in catalog.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}", soft_wrap=True)


@template_app.command("cp")
def template_cp(
    from_name: Annotated[str, Option("--from", help="Built-in template to copy")],
    to_name: Annotated[
        str | None,
        Option("--to", help="Name for the custom copy (defaults to --from)"),
    ] = None,
    custom_root: Annotated[
        Path | None,
        Option("--custom-root", help="Override the custom template directory"),
    ] = None,
) -> None:
    """Copy a built-in template into your custom templates directory."""
    try:
        destination = copy_builtin_to_custom(
            from_name, target_name=to_name, custom_root=custom_root
        )
    except TemplateError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=1) from exc
    except FileExistsError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise Exit(code=2) from exc

    console.print(f"[green]Copied template to:[/green] {destination}")


@template_app.command("validate")
def template_validate(
    name: Annotated[
        str | None,
        Argument(help="Template name to validate (default: all templates)"),
    ] = None,
    origin: Annotated[
        str | None,
        Option("--origin", help="Origin filter: built-in or custom"),
    ] = None,
) -> None:
    """Validate one or all templates."""
    if name is not None:
        errors = validate_template(name, origin=origin)
        if errors:
            console.print(f"[red]Template '{name}' is invalid:[/red]")
            for error in errors:
                console.print(f"  ✗ {error}", soft_wrap=True)
            raise Exit(code=1)
        console.print(f"[green]Template '{name}' is valid[/green]")
        return

    templates = discover_templates()
    failed = False
    console.print("Template validation")
    for entry in templates:
        errors = validate_template(entry["name"], origin=entry["origin"])
        if errors:
            failed = True
            console.print(
                f"  [red]✗[/red] {entry['name']} ({entry['origin']}): invalid",
                soft_wrap=True,
            )
            for error in errors:
                console.print(f"      {error}", soft_wrap=True)
        else:
            console.print(f"  [green]✓[/green] {entry['name']} ({entry['origin']}): valid")

    if failed:
        raise Exit(code=1)
