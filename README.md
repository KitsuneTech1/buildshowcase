# buildshowcase

Turn a group of project folders into an honest static launch site.

## What it does

Given a list of project directories, buildshowcase:
- Scans each for README, test files, dependencies, and code metrics
- Scores each project on quality (tests, documentation, dependencies, size)
- Generates a static HTML portfolio page
- Ranks projects by score

Output is a single self-contained HTML file with no external dependencies.

## Installation

```bash
pip install -e .
```

Or run directly:

```bash
python showcase.py <repo1> [repo2] [repo3] ... [options]
```

## Usage

### Basic usage

Generate a portfolio from project folders:

```bash
python showcase.py ~/projects/project-a ~/projects/project-b ~/projects/project-c
```

This creates index.html in the current directory.

### Custom output filename

```bash
python showcase.py ~/projects/* --output portfolio.html
```

### Custom title

```bash
python showcase.py ~/projects/* --title "My Work"
```

### Multiple options

```bash
python showcase.py ~/projects/a ~/projects/b --output my-portfolio.html --title "Software Engineering"
```

## Output

The generated HTML file is a static, self-contained portfolio page that:
- Lists all projects in cards
- Shows project name and description (from README)
- Displays quality score for each project (0-100)
- Ranks projects by score, highest first
- Uses clean, responsive CSS

Open the generated index.html in any browser. No server or build step required.

## Scoring

Each project is scored 0-100 on:
- Tests: presence of test files (0-25 points)
- Documentation: README and docs/ directory (0-25 points)
- Dependencies: package.json, pyproject.toml, Cargo.toml, etc. (0-25 points)
- Size: favors focused projects under 50 source files (0-25 points)

## Testing

```bash
python -m unittest test_showcase
```

## Example

```bash
$ python showcase.py ~/code/tool-a ~/code/tool-b ~/code/tool-c
Generated showcase: index.html
Projects: 3
  tool-b                          89/100
  tool-a                          76/100
  tool-c                          54/100
```

## License

MIT License

Copyright (c) 2026 KitsuneTech1
