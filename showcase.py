#!/usr/bin/env python3
"""Build a self-contained portfolio site from local project folders."""

import base64
import html
import mimetypes
import os
import sys
import tempfile
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
MAX_README_BYTES = 1024 * 1024
MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024


def _is_safe_regular_file(path, max_bytes=None):
    """Return whether path is a non-symlink regular file within the size limit."""
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file():
            return False
        return max_bytes is None or path.stat().st_size <= max_bytes
    except OSError:
        return False


def _bounded_int(value, default=0, maximum=None):
    """Convert display data to an integer without letting malformed input crash rendering."""
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        result = default
    if maximum is not None:
        result = max(0, min(maximum, result))
    return result


def _is_within_root(root, path):
    """Return whether path resolves beneath root without following an escape."""
    try:
        root = Path(root).resolve()
        path = Path(path).resolve(strict=True)
        path.relative_to(root)
        return True
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _read_bounded_bytes(path, max_bytes):
    """Read a regular file while enforcing a hard byte limit."""
    if not _is_safe_regular_file(path, max_bytes):
        raise OSError("file is not a readable regular file within the size limit")
    with Path(path).open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise OSError("file exceeds the size limit")
    return data


def _iter_files(repo_path):
    """Yield repository files while skipping generated and dependency folders."""
    repo_path = Path(repo_path)
    for root, directories, filenames in os.walk(repo_path, topdown=True, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRS
            and not directory.startswith(".")
            and not (Path(root) / directory).is_symlink()
        )
        for filename in sorted(filenames):
            path = Path(root) / filename
            if not path.is_symlink():
                yield path


def _find_readme(repo_path):
    repo_path = Path(repo_path)
    for name in README_NAMES:
        candidate = repo_path / name
        if _is_safe_regular_file(candidate):
            return candidate
    readme_names = {name.lower() for name in README_NAMES}
    return next(
        (candidate for candidate in repo_path.iterdir()
         if _is_safe_regular_file(candidate) and candidate.name.lower() in readme_names),
        None,
    )


def _is_test_file(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    stem = path.stem.lower()
    return (
        path.parent.name.lower() in {"test", "tests"}
        or (
            suffix in SOURCE_EXTENSIONS
            and (
                name.startswith("test")
                or stem.endswith(("_test", ".test", "_spec", ".spec"))
            )
        )
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
    try:
        readme = _find_readme(repo_path)
    except OSError:
        return "No description available"
    if readme and _is_safe_regular_file(readme, MAX_README_BYTES):
        try:
            text = _read_bounded_bytes(readme, MAX_README_BYTES).decode(
                "utf-8", errors="replace"
            )
        except OSError:
            return "No description available"
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
    try:
        limit = int(limit)
    except (TypeError, ValueError, OverflowError):
        return []
    if limit <= 0:
        return []
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
    encoded = base64.b64encode(_read_bounded_bytes(path, MAX_SCREENSHOT_BYTES)).decode("ascii")
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


def _render_screenshots(project, rendered_screenshot_counts=None):
    screenshots = []
    repo_path = project.get("path")
    for path in project.get("screenshots", []) or []:
        if not repo_path or not _is_within_root(repo_path, path):
            continue
        try:
            uri = _image_data_uri(path)
        except (OSError, TypeError, ValueError):
            continue
        alt = html.escape(Path(path).stem.replace("_", " ").replace("-", " "))
        screenshots.append(f'<img src="{uri}" alt="{alt}" loading="lazy">')
    if rendered_screenshot_counts is not None:
        rendered_screenshot_counts[id(project)] = len(screenshots)
    if not screenshots:
        return '<p class="no-screenshot">No screenshots found.</p>'
    return '<div class="screenshots">' + "".join(screenshots) + '</div>'


def build_html(projects, output_path, title="Portfolio", rendered_screenshot_counts=None):
    """Generate a static, self-contained HTML portfolio page."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    projects_sorted = sorted(
        projects,
        key=lambda project: (
            -_bounded_int(project.get("score", 0), maximum=100),
            str(project.get("name", "")).casefold(),
        ),
    )
    safe_title = html.escape(str(title))

    cards = []
    for project in projects_sorted:
        name = html.escape(str(project.get("name", "Unnamed project")))
        description = html.escape(str(project.get("description", "No description available")))
        score = _bounded_int(project.get("score", 0), maximum=100)
        breakdown = project.get("breakdown", {})
        if not isinstance(breakdown, dict):
            breakdown = {}
        details = " / ".join(
            f"{label}: {_bounded_int(breakdown.get(key, 0), maximum=25)}/25"
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
                {_render_screenshots(project, rendered_screenshot_counts)}
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
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(html_text)
        os.replace(temporary_path, output_path)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise
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
        try:
            projects.append(scan_repo(path))
        except OSError as error:
            print(f"Warning: could not read {path}, skipping ({error})", file=sys.stderr)
            continue

    if not projects:
        print("Error: No valid repositories found", file=sys.stderr)
        return 1

    rendered_screenshot_counts = {}
    output_path = build_html(
        projects,
        args.output,
        args.title,
        rendered_screenshot_counts=rendered_screenshot_counts,
    )
    print(f"Generated showcase: {output_path}")
    print(f"Projects: {len(projects)}")
    for project in sorted(projects, key=lambda item: (-item["score"], item["name"].casefold())):
        screenshot_count = rendered_screenshot_counts.get(id(project), 0)
        visual_note = f", screenshots: {screenshot_count}" if screenshot_count else ""
        print(f"  {project['name']:30} {project['score']:3}/100{visual_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
