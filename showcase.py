#!/usr/bin/env python3
"""Build a self-contained portfolio site from local project folders."""

import base64
import html
import mimetypes
import os
import sys
from argparse import ArgumentParser
from pathlib import Path


IGNORED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", "node_modules",
    "venv", ".venv", "env", ".env", "dist", "build",
}
SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
    ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx",
}
DEPENDENCY_FILES = {
    "cargo.toml", "composer.json", "go.mod", "package.json", "pipfile",
    "poetry.lock", "project.toml", "pyproject.toml", "requirements.txt",
    "setup.cfg", "setup.py",
}
SCREENSHOT_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
SCREENSHOT_DIRS = {"demo", "demos", "screenshot", "screenshots"}
README_NAMES = ("README.md", "README.rst", "README.txt")


def _iter_files(repo_path):
    """Yield repository files while skipping generated and dependency folders."""
    repo_path = Path(repo_path)
    for root, directories, filenames in os.walk(repo_path, topdown=True, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRS and not directory.startswith(".")
        )
        for filename in sorted(filenames):
            yield Path(root) / filename


def _find_readme(repo_path):
    repo_path = Path(repo_path)
    for name in README_NAMES:
        candidate = repo_path / name
        if candidate.is_file():
            return candidate
    readme_names = {name.lower() for name in README_NAMES}
    return next(
        (candidate for candidate in repo_path.iterdir()
         if candidate.is_file() and candidate.name.lower() in readme_names),
        None,
    )


def _is_test_file(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    return (
        path.parent.name.lower() in {"test", "tests"}
        or (name.startswith("test") and suffix in SOURCE_EXTENSIONS)
        or name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx", ".spec.js", ".spec.ts"))
    )


def score_breakdown(repo_path):
    """Return the four score components for a repository, each capped at 25."""
    repo_path = Path(repo_path)
    files = list(_iter_files(repo_path))
    test_directories = {path.parent for path in files if _is_test_file(path)}
    tests = min(25, len(test_directories) * 10)

    docs = 10 if _find_readme(repo_path) else 0
    docs += 15 if (repo_path / "docs").is_dir() else 0
    docs = min(25, docs)

    dependency_files = {
        path.name.lower()
        for path in files
        if path.parent == repo_path and path.name.lower() in DEPENDENCY_FILES
    }
    dependencies = 25 if dependency_files else 0

    source_count = sum(1 for path in files if path.suffix.lower() in SOURCE_EXTENSIONS)
    if source_count < 20:
        size = 25
    elif source_count < 50:
        size = 20
    else:
        size = 10

    return {
        "tests": tests,
        "documentation": docs,
        "dependencies": dependencies,
        "size": size,
    }


def score_repo(repo_path):
    """Return a quick 0-100 score without importing project dependencies."""
    return sum(score_breakdown(repo_path).values())


def get_repo_name(repo_path):
    """Get the final directory name for a repository."""
    path = Path(repo_path)
    return path.name or path.resolve().name


def get_repo_description(repo_path):
    """Extract the first useful paragraph line from a repository README."""
    readme = _find_readme(repo_path)
    if readme:
        text = readme.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!["):
                continue
            if stripped.startswith("[!["):
                continue
            return stripped
    return "No description available"


def find_screenshots(repo_path, limit=3):
    """Find likely screenshots without treating every repository image as one."""
    repo_path = Path(repo_path)
    candidates = []
    for path in _iter_files(repo_path):
        if path.suffix.lower() not in SCREENSHOT_EXTENSIONS:
            continue
        relative = path.relative_to(repo_path)
        directories = {part.lower() for part in relative.parts[:-1]}
        stem = path.stem.lower()
        if directories & SCREENSHOT_DIRS or any(
            word in stem for word in ("screenshot", "screen-shot", "preview", "demo")
        ):
            candidates.append(path)
    return sorted(
        candidates,
        key=lambda path: path.relative_to(repo_path).as_posix().casefold(),
    )[:limit]


def _image_data_uri(path):
    path = Path(path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def scan_repo(repo_path):
    """Collect the local data used to render one project card."""
    repo_path = Path(repo_path)
    breakdown = score_breakdown(repo_path)
    return {
        "name": get_repo_name(repo_path),
        "description": get_repo_description(repo_path),
        "score": sum(breakdown.values()),
        "breakdown": breakdown,
        "screenshots": find_screenshots(repo_path),
        "path": str(repo_path),
    }


def _render_screenshots(project):
    screenshots = []
    for path in project.get("screenshots", []):
        try:
            uri = _image_data_uri(path)
        except (OSError, ValueError):
            continue
        alt = html.escape(Path(path).stem.replace("_", " ").replace("-", " "))
        screenshots.append(f'<img src="{uri}" alt="{alt}" loading="lazy">')
    if not screenshots:
        return '<p class="no-screenshot">No screenshots found.</p>'
    return '<div class="screenshots">' + "".join(screenshots) + '</div>'


def build_html(projects, output_path, title="Portfolio"):
    """Generate a static, self-contained HTML portfolio page."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    projects_sorted = sorted(
        projects,
        key=lambda project: (-int(project.get("score", 0)), str(project.get("name", "")).casefold()),
    )
    safe_title = html.escape(str(title))

    cards = []
    for project in projects_sorted:
        name = html.escape(str(project.get("name", "Unnamed project")))
        description = html.escape(str(project.get("description", "No description available")))
        score = int(project.get("score", 0))
        breakdown = project.get("breakdown", {})
        details = " / ".join(
            f"{label}: {int(breakdown.get(key, 0))}/25"
            for key, label in (
                ("tests", "Tests"),
                ("documentation", "Docs"),
                ("dependencies", "Dependencies"),
                ("size", "Size"),
            )
        )
        cards.append(
            f'''            <article class="project">
                <h2>{name}</h2>
                <p>{description}</p>
                {_render_screenshots(project)}
                <div class="score">Score: {score}/100</div>
                <p class="breakdown">{html.escape(details)}</p>
            </article>
'''
        )

    html_text = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; font-family: system-ui, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        header {{ background: #fff; border-bottom: 1px solid #ddd; padding: 40px 20px; text-align: center; }}
        header h1 {{ margin: 0 0 10px; font-size: 2.5em; }}
        header p {{ margin: 0; color: #666; }}
        main {{ max-width: 1200px; margin: 40px auto; padding: 0 20px; }}
        .projects {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .project {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; }}
        .project h2 {{ margin: 0 0 10px; font-size: 1.3em; color: #0645ad; }}
        .project > p {{ color: #666; margin: 0 0 15px; }}
        .screenshots {{ display: grid; gap: 10px; margin: 0 0 15px; }}
        .screenshots img {{ display: block; width: 100%; max-height: 260px; object-fit: contain; background: #eee; border-radius: 4px; }}
        .no-screenshot {{ font-size: .9em; font-style: italic; }}
        .score {{ background: #f0f0f0; border-radius: 4px; padding: 10px; text-align: center; font-weight: bold; }}
        .breakdown {{ font-size: .85em; margin: 10px 0 0 !important; }}
        footer {{ margin-top: 60px; padding: 40px 20px; text-align: center; color: #777; background: #fff; border-top: 1px solid #ddd; }}
    </style>
</head>
<body>
    <header>
        <h1>{safe_title}</h1>
        <p>Local projects ranked by a small set of visible checks.</p>
    </header>
    <main>
        <section class="projects">
{''.join(cards)}        </section>
    </main>
    <footer><p>Generated with buildshowcase.</p></footer>
</body>
</html>
'''
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def main(argv=None):
    parser = ArgumentParser(description="Build a static portfolio showcase.")
    parser.add_argument("repos", nargs="+", help="Paths to repository folders")
    parser.add_argument("--output", default="index.html", help="Output HTML file (default: index.html)")
    parser.add_argument("--title", default="Portfolio", help="Site title (default: Portfolio)")
    args = parser.parse_args(argv)

    projects = []
    for repo_path in args.repos:
        path = Path(repo_path)
        if not path.is_dir():
            print(f"Warning: {path} is not a directory, skipping", file=sys.stderr)
            continue
        projects.append(scan_repo(path))

    if not projects:
        print("Error: No valid repositories found", file=sys.stderr)
        return 1

    output_path = build_html(projects, args.output, args.title)
    print(f"Generated showcase: {output_path}")
    print(f"Projects: {len(projects)}")
    for project in sorted(projects, key=lambda item: (-item["score"], item["name"].casefold())):
        screenshot_count = len(project["screenshots"])
        visual_note = f", screenshots: {screenshot_count}" if screenshot_count else ""
        print(f"  {project['name']:30} {project['score']:3}/100{visual_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
