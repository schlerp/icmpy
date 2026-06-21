from __future__ import annotations

import platform
from pathlib import Path

import pytest
from typer.testing import CliRunner

from icmpy.builder import (
    TemplateError,
    build_workspace,
    copy_builtin_to_custom,
    discover_templates,
    resolve_template,
)
from icmpy.cli import app
from icmpy.template_catalog import (
    AmbiguousTemplateName,
    TemplateCatalog,
    TemplateOrigin,
    get_custom_template_root,
    parse_frontmatter,
    validate_custom_template,
)

runner = CliRunner()


def _create_custom_template(
    root: Path,
    name: str,
    *,
    purpose: str = "A custom template",
    with_stages: bool = True,
    extra_files: dict[str, str] | None = None,
) -> Path:
    template_dir = root / name
    template_dir.mkdir(parents=True, exist_ok=True)
    context = f"---\npurpose: {purpose}\n---\n\n# {name}\n"
    (template_dir / "CONTEXT.md").write_text(context, encoding="utf-8")
    (template_dir / "questionnaire.json").write_text("[]", encoding="utf-8")

    if with_stages:
        stage = template_dir / "stages" / "01_research"
        stage.mkdir(parents=True)
        (stage / "CONTEXT.md").write_text(
            """# Research

## Inputs

- Source material

## Process

Analyze.

## Outputs

- summary.md
""",
            encoding="utf-8",
        )

    for relative, content in (extra_files or {}).items():
        path = template_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    return template_dir


def test_parse_frontmatter_basic() -> None:
    text = "---\npurpose: Hello world\n---\n"
    result = parse_frontmatter(text)
    assert result == {"purpose": "Hello world"}


def test_parse_frontmatter_inline_list() -> None:
    text = "---\ntags: [a, b, c]\n---\n"
    result = parse_frontmatter(text)
    assert result == {"tags": ["a", "b", "c"]}


def test_get_custom_root_with_xdg_config_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    assert get_custom_template_root() == xdg / "icmpy" / "templates"


def test_get_custom_root_prefers_dot_config_on_macos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    (tmp_path / ".config").mkdir()
    assert get_custom_template_root() == tmp_path / ".config" / "icmpy" / "templates"


def test_get_custom_root_falls_back_on_macos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import platformdirs

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        platformdirs,
        "user_config_dir",
        lambda appname, **kwargs: str(tmp_path / "Library" / "Application Support" / appname),
    )
    assert (
        get_custom_template_root()
        == tmp_path / "Library" / "Application Support" / "icmpy" / "templates"
    )


def test_template_catalog_discovers_builtins() -> None:
    catalog = TemplateCatalog(custom_root=Path("/nonexistent"))
    names = {t.name for t in catalog.templates}
    assert "empty" in names


def test_template_catalog_discovers_custom(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "my-custom", purpose="Custom purpose")

    catalog = TemplateCatalog(custom_root=custom_root)
    templates = {t.name: t for t in catalog.templates}

    assert "my-custom" in templates
    assert templates["my-custom"].origin == TemplateOrigin.CUSTOM
    assert templates["my-custom"].description == "Custom purpose"
    assert "empty" in templates
    assert templates["empty"].origin == TemplateOrigin.BUILTIN


def test_template_catalog_warns_about_loose_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    custom_root = tmp_path / "custom"
    custom_root.mkdir()
    (custom_root / "notes.md").write_text("notes")

    catalog = TemplateCatalog(custom_root=custom_root)
    assert len(catalog.warnings) == 1
    assert "notes.md" in catalog.warnings[0]


def test_template_catalog_ambiguous_template_name(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "empty", purpose="Overrides empty")

    catalog = TemplateCatalog(custom_root=custom_root)
    with pytest.raises(AmbiguousTemplateName):
        catalog.get("empty")

    builtin = catalog.get("empty", origin=TemplateOrigin.BUILTIN)
    assert builtin.origin == TemplateOrigin.BUILTIN
    custom = catalog.get("empty", origin=TemplateOrigin.CUSTOM)
    assert custom.origin == TemplateOrigin.CUSTOM


def test_resolve_template_requires_origin_when_ambiguous(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "empty", purpose="Overrides empty")

    with pytest.raises(TemplateError, match="ambiguous"):
        resolve_template("empty", custom_root=custom_root)

    result = resolve_template("empty", origin="built-in", custom_root=custom_root)
    assert result["origin"] == "built-in"


def test_validate_custom_template_missing_context_md(tmp_path: Path) -> None:
    template_dir = tmp_path / "bad"
    template_dir.mkdir()
    errors = validate_custom_template(template_dir)
    assert len(errors) == 1
    assert "Missing CONTEXT.md" in errors[0]


def test_validate_custom_template_missing_purpose(tmp_path: Path) -> None:
    template_dir = tmp_path / "bad"
    template_dir.mkdir()
    (template_dir / "CONTEXT.md").write_text("---\nfoo: bar\n---\n", encoding="utf-8")
    errors = validate_custom_template(template_dir)
    assert any("purpose" in err for err in errors)


def test_copy_builtin_to_custom(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    destination = copy_builtin_to_custom("empty", custom_root=custom_root)

    assert destination == custom_root / "empty"
    assert destination.is_dir()
    assert (destination / "questionnaire.json").is_file()
    assert (destination / "CONTEXT.md").is_file()
    assert "purpose:" in (destination / "CONTEXT.md").read_text()


def test_copy_builtin_to_custom_rejects_existing(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    (custom_root / "empty").mkdir(parents=True)

    with pytest.raises(FileExistsError):
        copy_builtin_to_custom("empty", custom_root=custom_root)


def test_discover_templates_unified(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "my-custom", purpose="Custom")

    templates = discover_templates(custom_root=custom_root)
    by_name = {t["name"]: t for t in templates}
    assert by_name["my-custom"]["origin"] == "custom"
    assert by_name["empty"]["origin"] == "built-in"


def test_build_workspace_from_custom_template(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "my-custom", purpose="Mine")

    workspace = build_workspace(
        "my-custom",
        tmp_path,
        answers={"workspace_name": "from-custom"},
        validate=True,
        origin="custom",
        custom_root=custom_root,
    )

    assert workspace.is_dir()
    assert (workspace / "CLAUDE.md").is_file()
    assert (workspace / "stages" / "01_research" / "CONTEXT.md").is_file()


def test_build_create_ambiguous_requires_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "empty", purpose="Overrides empty")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(
        app,
        ["build", "create", "--template", "empty", "--target", str(tmp_path)],
    )
    assert result.exit_code == 1
    assert "ambiguous" in result.output.lower()


def test_build_create_with_origin_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "empty", purpose="Overrides empty")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    target = tmp_path / "built"
    result = runner.invoke(
        app,
        ["build", "create", "--template", "empty", "--origin", "custom", "--target", str(target)],
    )
    assert result.exit_code == 0, result.output
    assert (target / "empty" / "CLAUDE.md").is_file()


def test_cli_template_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    result = runner.invoke(app, ["template", "path"])
    assert result.exit_code == 0
    assert str(tmp_path / "config" / "icmpy" / "templates") in result.output


def test_cli_template_path_create(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    result = runner.invoke(app, ["template", "path", "--create"])
    assert result.exit_code == 0
    assert (tmp_path / "config" / "icmpy" / "templates").is_dir()


def test_cli_template_list_shows_builtins_and_customs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "my-custom", purpose="Mine")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "list"])
    assert result.exit_code == 0, result.output
    assert "my-custom" in result.output
    assert "custom" in result.output
    assert "empty" in result.output


def test_cli_template_list_notes_shadowing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "empty", purpose="Overrides empty")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "list"])
    assert result.exit_code == 0, result.output
    assert "shadows built-in" in result.output
    assert "shadowed" in result.output


def test_cli_template_list_warns_loose_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_root = tmp_path / "custom"
    custom_root.mkdir(parents=True)
    (custom_root / "notes.md").write_text("notes")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "list"])
    assert result.exit_code == 0, result.output
    assert "notes.md" in result.output
    assert "Ignoring loose file" in result.output


def test_cli_template_cp(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "template",
            "cp",
            "--from",
            "empty",
            "--custom-root",
            str(tmp_path / "custom"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "custom" / "empty" / "CONTEXT.md").is_file()


def test_cli_template_cp_fails_when_destination_exists(tmp_path: Path) -> None:
    existing = tmp_path / "custom" / "empty"
    existing.mkdir(parents=True)

    result = runner.invoke(
        app,
        [
            "template",
            "cp",
            "--from",
            "empty",
            "--custom-root",
            str(tmp_path / "custom"),
        ],
    )
    assert result.exit_code == 2


def test_cli_template_validate_missing_purpose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "bad", purpose="Bad")
    bad_dir = custom_root / "bad"
    (bad_dir / "CONTEXT.md").write_text("---\nfoo: bar\n---\n", encoding="utf-8")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "validate", "bad"])
    assert result.exit_code == 1, result.output
    assert "purpose" in result.output
    assert str(bad_dir / "CONTEXT.md") in result.output


def test_cli_template_validate_all_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "good", purpose="Good")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "validate"])
    assert result.exit_code == 0, result.output
    assert "empty" in result.output


def test_cli_template_validate_named_custom(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom_root = tmp_path / "custom"
    _create_custom_template(custom_root, "good", purpose="Good")
    monkeypatch.setattr("icmpy.template_catalog.get_custom_template_root", lambda: custom_root)

    result = runner.invoke(app, ["template", "validate", "good"])
    assert result.exit_code == 0, result.output
    assert "valid" in result.output.lower()


def test_custom_template_allows_symlinked_directory(tmp_path: Path) -> None:
    custom_root = tmp_path / "custom"
    shared = tmp_path / "shared" / "shared-template"
    shared.mkdir(parents=True)
    (shared / "CONTEXT.md").write_text("---\npurpose: Shared\n---\n", encoding="utf-8")
    (shared / "questionnaire.json").write_text("[]", encoding="utf-8")

    custom_root.mkdir(parents=True)
    (custom_root / "shared-template").symlink_to(shared, target_is_directory=True)

    catalog = TemplateCatalog(custom_root=custom_root)
    templates = {t.name: t for t in catalog.templates}
    assert "shared-template" in templates


def test_template_catalog_malformed_frontmatter_is_skipped(
    tmp_path: Path,
) -> None:
    custom_root = tmp_path / "custom"
    template_dir = custom_root / "broken"
    template_dir.mkdir(parents=True)
    (template_dir / "CONTEXT.md").write_text("---\n: bad yaml\n---\n", encoding="utf-8")

    catalog = TemplateCatalog(custom_root=custom_root)
    assert "broken" not in {t.name for t in catalog.templates}
    assert any("broken" in w for w in catalog.warnings)
