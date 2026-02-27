"""RingBot CLI: AI-powered ring design from natural language descriptions."""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="ringbot")
def cli():
    """RingBot - AI-powered jewelry ring designer."""


@cli.command()
@click.argument("description")
@click.option(
    "--provider", "-p",
    type=click.Choice(["openai", "anthropic"], case_sensitive=False),
    default=None,
    help="AI provider (default: from .env or openai).",
)
@click.option(
    "--ring-size", "-s",
    type=float,
    default=None,
    help="US ring size (default: from .env or 7).",
)
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Design seed for reproducibility (random if omitted).",
)
@click.option(
    "--format", "-f",
    "formats",
    type=click.Choice(["step", "stl", "obj"], case_sensitive=False),
    multiple=True,
    default=("step", "stl", "obj"),
    help="Output format(s).",
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Custom output directory (auto-generated if omitted).",
)
@click.option("--no-viewer", is_flag=True, help="Skip launching the 3D viewer.")
@click.option("--viewer-port", type=int, default=8765, help="Port for the 3D viewer.")
def design(
    description: str,
    provider: str | None,
    ring_size: float | None,
    seed: int | None,
    formats: tuple[str, ...],
    output_dir: Path | None,
    no_viewer: bool,
    viewer_port: int,
):
    """Design a ring from a natural-language description.

    Example:

        ringbot design "A feminine 18k gold nature inspired ring with leaf elements"
    """
    click.secho("\n  RingBot - AI Ring Designer\n", fg="yellow", bold=True)

    # --- Step 1: AI Interpretation ---
    click.secho("  [1/5] Interpreting description with AI...", fg="cyan")
    try:
        from ringbot.ai.interpreter import interpret_description
        spec = interpret_description(
            description,
            provider_name=provider,
            ring_size=ring_size,
            design_seed=seed,
        )
    except Exception as exc:
        click.secho(f"  Error: {exc}", fg="red")
        sys.exit(1)

    click.secho(f"        Material: {spec.band.material.value}", fg="white")
    click.secho(f"        Band: {spec.band.profile.value}, {spec.band.width_mm}mm x {spec.band.thickness_mm}mm", fg="white")
    if spec.center_stone:
        click.secho(f"        Center: {spec.center_stone.carat}ct {spec.center_stone.gem_type.value} ({spec.center_stone.cut.value})", fg="white")
    for s in spec.accent_stones:
        click.secho(f"        Accent: {s.count}x {s.carat}ct {s.gem_type.value} ({s.cut.value})", fg="white")
    for d in spec.decorative_elements:
        click.secho(f"        Decor: {d.element_type.value} ({d.position.value})", fg="white")
    click.secho(f"        Seed: {spec.design_seed}", fg="white")

    # --- Step 2: Pre-generation validation ---
    click.secho("\n  [2/5] Validating spec...", fg="cyan")
    from ringbot.validation.manufacturability import validate_spec
    pre_report = validate_spec(spec)
    if not pre_report.passed:
        click.secho("  Pre-generation validation FAILED:", fg="red")
        click.echo(pre_report.summary())
        sys.exit(1)
    click.secho("        Pre-generation checks passed.", fg="green")

    # --- Step 3: Generate 3D model ---
    click.secho("\n  [3/5] Generating 3D model...", fg="cyan")
    try:
        from ringbot.generator.ring_builder import build_ring
        assembly = build_ring(spec)
    except Exception as exc:
        click.secho(f"  Error during generation: {exc}", fg="red")
        sys.exit(1)
    click.secho("        3D model generated successfully.", fg="green")

    # --- Step 4: Post-generation validation + export ---
    click.secho("\n  [4/5] Validating & exporting...", fg="cyan")
    from ringbot.validation.manufacturability import full_validation
    report = full_validation(spec, assembly.metal)
    click.echo(f"\n{report.summary()}\n")

    from ringbot.export.exporter import export_assembly
    result = export_assembly(
        assembly,
        validation_report=report,
        formats=list(formats),
        output_dir=output_dir,
    )
    click.secho(f"        Output: {result['output_dir']}", fg="green")
    for fmt, path in result["files"].items():
        click.secho(f"          {fmt}: {path}", fg="white")

    # --- Step 5: Viewer ---
    if not no_viewer and "stl" in formats:
        click.secho("\n  [5/5] Launching 3D viewer...", fg="cyan")
        from ringbot.viewer.server import launch_viewer
        launch_viewer(result["output_dir"], port=viewer_port)
    else:
        click.secho("\n  Done!", fg="yellow", bold=True)


@cli.command()
@click.argument("output_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--port", type=int, default=8765)
def view(output_dir: Path, port: int):
    """Open the 3D viewer for an existing output directory."""
    from ringbot.viewer.server import launch_viewer
    launch_viewer(output_dir, port=port)


if __name__ == "__main__":
    cli()
