<p align="center"><a href="https://kitsunetechnologies.org/work"><img src="https://raw.githubusercontent.com/KitsuneTech1/.github/main/assets/kitsune-banner.svg" alt="Built by Kitsune Technologies" width="760"></a></p>

# buildshowcase

Turn a group of local project folders into a static portfolio page.

## What it does

Given a list of project directories, buildshowcase:
- Reads local files only. It does not call a network service or need an API token.
- Checks for a README, test files, dependency manifests, and source-file count.
- Scores each project from 0 to 100 and shows the four score components.
- Finds likely screenshots in `screenshots/`, `demo/`, or files named `preview` or `screenshot`, then embeds them in the HTML.
- Ranks projects by score, with project name as the tie breaker.

Output is a single self-contained HTML file with no external dependencies.

## Installation

There is no package metadata yet, so run the script directly:

```bash
python showcase.py <repo1> [repo2] [repo3] ... [options]
```

The repository includes three small example projects under `projects/`, so the
commands below work immediately after a fresh checkout.

## Usage

The examples below use paths relative to the current directory. Pass project folders explicitly so the commands work in PowerShell and Unix-like shells.

### Basic usage

Generate a portfolio from project folders:

```bash
python showcase.py projects/project-a projects/project-b projects/project-c
```

This creates `index.html` in the current directory. Existing screenshot files are embedded, so the result does not need the source folders to display them.

### Custom output filename

```bash
python showcase.py projects/project-a projects/project-b --output portfolio.html
```

### Custom title

```bash
python showcase.py projects/project-a projects/project-b --title "My Work"
```

### Multiple options

```bash
python showcase.py projects/project-a projects/project-b --output my-portfolio.html --title "Software Engineering"
```

## Output

The generated HTML file is a static, self-contained portfolio page that:
- Lists all projects in cards
- Shows project name and description (from README)
- Displays quality score for each project (0-100)
- Ranks projects by score, highest first
- Uses clean, responsive CSS

Open the generated HTML file in a browser. No server or build step is required.

Directories that do not exist are skipped with a warning. If every supplied path is invalid, the command exits with status 1.

## Scoring

Each project is scored 0-100 on four capped components:
- Tests: test files or test directories (0-25 points)
- Documentation: a README and `docs/` directory (0-25 points)
- Dependencies: a common dependency manifest in the project root (0-25 points)
- Size: source-file count, with smaller projects receiving more points (0-25 points)

The score measures visible repository signals. It does not run tests, inspect code quality, or prove that a project works.

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
