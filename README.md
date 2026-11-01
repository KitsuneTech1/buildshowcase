<p align="center"><a href="https://kitsunetechnologies.org/work"><img src="https://raw.githubusercontent.com/KitsuneTech1/.github/main/assets/kitsune-banner.svg" alt="Built by Kitsune Technologies" width="760"></a></p>

# Shipboard

Turn a group of project folders into a static portfolio page. (Repo: buildshowcase)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)

## Quick start

Run the script directly with project folders:

```bash
python showcase.py projects/project-a projects/project-b projects/project-c
```

This generates `index.html` with a ranked portfolio of your projects. The example projects in this repo work out of the box.

Open the HTML file in a browser. No server or dependencies needed.

## What it does

For each project folder, Shipboard:
- Reads local files only; no network calls or API tokens.
- Checks for a README, tests, dependency manifests, and source file count.
- Scores each project 0-100 and breaks down the four score components.
- Finds and embeds screenshots from common directories (`screenshots/`, `demo/`) or files named `preview` or `screenshot`.
- Ranks projects by score, using project name as a tiebreaker.

Output is a single self-contained HTML file with clean, responsive CSS.

## Usage

Pass project folders as arguments. Use explicit paths so commands work in PowerShell and Unix shells:

### Basic usage

```bash
python showcase.py projects/project-a projects/project-b projects/project-c
```

Creates `index.html` in the current directory. Screenshots are embedded, so the file works without the source folders.

### Custom output filename

```bash
python showcase.py projects/project-a projects/project-b --output portfolio.html
```

### Custom title

```bash
python showcase.py projects/project-a projects/project-b --title "My Work"
```

### Combine options

```bash
python showcase.py projects/project-a projects/project-b --output my-portfolio.html --title "Software Engineering"
```

Missing directories are skipped with a warning. If all paths are invalid, the command exits with status 1.

## Scoring

Each project gets a 0-100 score based on four signals, each worth up to 25 points:
- Tests: test files or test directories found
- Documentation: README and/or docs/ directory
- Dependencies: package.json, pyproject.toml, Cargo.toml, or similar
- Size: source file count (smaller projects score higher)

The score reflects repository signals you can see without running code. It doesn't run tests, review code quality, or prove a project actually works.

## Testing

```bash
python -m unittest test_showcase
```

## Example

```bash
$ python showcase.py projects/project-a projects/project-b projects/project-c
Generated showcase: index.html
Projects: 3
  project-a                       85/100
  project-b                       60/100
  project-c                       35/100
```

## License

MIT. Copyright (c) 2026 Kitsune Technologies LLC. Do what you like with it, commercially or otherwise, just keep the copyright notice. Full text in [LICENSE](LICENSE).

---

<p align="center"><sub>Part of <b>Buildtober 2026</b>: 31 open source projects in 31 days. Built by <a href="https://kitsunetechnologies.org/work">Kitsune Technologies</a>. More at <a href="https://github.com/KitsuneTech1">github.com/KitsuneTech1</a>.</sub></p>
