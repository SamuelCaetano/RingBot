# RingBot - AI-Powered Jewelry Ring Designer

RingBot takes a natural-language description of a ring, interprets it using AI (OpenAI or Anthropic), and generates a manufacturable 3D model with proper topology and manufacturing constraints.

## Features

- **AI Interpretation** — Understands jewelry terminology (settings, cuts, materials, profiles) and converts plain English into precise parametric specs.
- **Parametric 3D Generation** — Uses CadQuery (B-rep solid modeling on OpenCascade) to produce watertight, manifold solids ready for casting or 3D printing.
- **Manufacturability Checks** — Validates wall thickness, prong dimensions, stone seats, weight estimates, and mesh integrity.
- **Multi-format Export** — STEP (precision CAD), STL (3D printing), and OBJ.
- **Browser 3D Viewer** — Opens an interactive Three.js viewer with metallic materials and orbit controls.
- **Unique Designs** — Seed-based randomisation ensures every design is unique yet reproducible.

## Installation

CadQuery requires the OpenCascade kernel. The recommended install is via conda:

```bash
conda create -n ringbot python=3.11
conda activate ringbot
conda install -c conda-forge cadquery

pip install -r requirements.txt
```

Copy the environment file and add your API keys:

```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and/or ANTHROPIC_API_KEY
```

## Usage

### Design a ring

```bash
python -m ringbot.main design "A feminine 18k gold nature inspired ring, with leaf like elements, a 2 carat diamond centerstone in the collet, and 2 marquise cut emeralds as accents on the sides of the diamond."
```

### Options

```
--provider, -p    AI provider: openai or anthropic (default: from .env)
--ring-size, -s   US ring size (default: 7)
--seed            Design seed for reproducibility
--format, -f      Output formats: step, stl, obj (default: all)
--output-dir, -o  Custom output directory
--no-viewer       Skip the browser 3D viewer
--viewer-port     Port for the viewer (default: 8765)
```

### View an existing design

```bash
python -m ringbot.main view output/20260226_abc12345/
```

## Architecture

```
User Description
  -> AI Interpreter (OpenAI / Anthropic)
    -> RingSpec (Pydantic model)
      -> CadQuery Ring Generator
        -> Band + Settings + Decorations + Stones
          -> Manufacturability Validation
            -> Export (STEP / STL / OBJ)
              -> Three.js Browser Viewer
```

## Project Structure

```
ringbot/
  main.py              CLI entry point
  config.py            Configuration & .env loading
  ai/
    interpreter.py     LLM orchestration
    providers.py       OpenAI/Anthropic abstraction
    prompts.py         Jewelry domain system prompts
  models/
    ring_spec.py       Pydantic data models
    jewelry_data.py    Carat-to-mm tables, ring sizes, materials
  generator/
    ring_builder.py    Assembly orchestrator
    band.py            Band profile generation
    settings.py        Stone setting generators
    decorations.py     Decorative elements (leaves, vines, etc.)
    stones.py          Display stone geometry
  validation/
    manufacturability.py  Manufacturing constraint checks
  export/
    exporter.py        Multi-format export
  viewer/
    server.py          Local HTTP server
    templates/
      viewer.html      Three.js viewer
```
