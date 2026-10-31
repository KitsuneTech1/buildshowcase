#!/usr/bin/env python3
"""Build a static portfolio site from a list of project folders."""

import json
import sys
from pathlib import Path
from argparse import ArgumentParser
import subprocess


def score_repo(repo_path):
    """Quick score of a repo without importing dependencies."""
    repo_path = Path(repo_path)

    tests = 0
    docs = 0
    deps = 0
    size = 0

    # Test count
    test_files = list(repo_path.glob('**/test*.py')) + list(repo_path.glob('**/test')) + \
                 list(repo_path.glob('**/*.test.js')) + list(repo_path.glob('**/tests'))
    tests = min(25, len(set(p.parent for p in test_files)) * 10)

    # Docs
    if (repo_path / 'README.md').exists():
        docs += 10
    if (repo_path / 'docs').is_dir():
        docs += 10
    docs = min(25, docs)

    # Dependencies
    if (repo_path / 'pyproject.toml').exists() or (repo_path / 'package.json').exists() or \
       (repo_path / 'Cargo.toml').exists():
        deps = 20

    # Size - count source files
    source_files = list(repo_path.glob('**/*.py')) + list(repo_path.glob('**/*.js')) + \
                   list(repo_path.glob('**/*.rs'))
    source_files = [f for f in source_files if not any(x in str(f) for x in ['__pycache__', 'node_modules', '.git'])]

    if len(source_files) < 20:
        size = 25
    elif len(source_files) < 50:
        size = 20
    else:
        size = 10

    return tests + docs + deps + size


def get_repo_name(repo_path):
    """Get repository name from directory."""
    return Path(repo_path).name


def get_repo_description(repo_path):
    """Extract description from README."""
    readme = Path(repo_path) / 'README.md'
    if readme.exists():
        lines = readme.read_text().split('\n')
        for i, line in enumerate(lines):
            if i > 0 and i < 5 and line.strip() and not line.startswith('#'):
                return line.strip()
    return "No description available"


def build_html(projects, output_path, title="Portfolio"):
    """Generate static HTML portfolio page."""
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + title + '''</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        header {
            background: #fff;
            border-bottom: 1px solid #ddd;
            padding: 40px 20px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        header p { font-size: 1.1em; color: #666; }
        main {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
        }
        .projects {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
        }
        .project {
            background: #fff;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e0e0e0;
            transition: box-shadow 0.2s;
        }
        .project:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .project h3 {
            font-size: 1.3em;
            margin-bottom: 10px;
            color: #0066cc;
        }
        .project p {
            color: #666;
            margin-bottom: 15px;
            min-height: 2.4em;
        }
        .score {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            text-align: center;
            font-weight: bold;
            color: #333;
        }
        footer {
            text-align: center;
            padding: 40px 20px;
            color: #999;
            background: #fff;
            border-top: 1px solid #ddd;
            margin-top: 60px;
        }
    </style>
</head>
<body>
    <header>
        <h1>''' + title + '''</h1>
        <p>A collection of projects, ranked by quality metrics.</p>
    </header>
    <main>
        <section class="projects">
'''

    # Add project cards, sorted by score descending
    projects_sorted = sorted(projects, key=lambda p: p['score'], reverse=True)

    for project in projects_sorted:
        score_pct = int((project['score'] / 100) * 100)
        html += f'''            <div class="project">
                <h3>{project['name']}</h3>
                <p>{project['description']}</p>
                <div class="score">Score: {project['score']}/100</div>
            </div>
'''

    html += '''        </section>
    </main>
    <footer>
        <p>Generated with buildshowcase. Updated: 2026-10-31</p>
    </footer>
</body>
</html>
'''

    output_path = Path(output_path)
    output_path.write_text(html)
    return output_path


def main():
    parser = ArgumentParser(description='Build a static portfolio showcase.')
    parser.add_argument('repos', nargs='+', help='Paths to repository folders')
    parser.add_argument('--output', default='index.html', help='Output HTML file (default: index.html)')
    parser.add_argument('--title', default='Portfolio', help='Site title (default: Portfolio)')

    args = parser.parse_args()

    projects = []
    for repo_path in args.repos:
        repo_path = Path(repo_path)
        if not repo_path.is_dir():
            print(f"Warning: {repo_path} is not a directory, skipping", file=sys.stderr)
            continue

        name = get_repo_name(repo_path)
        description = get_repo_description(repo_path)
        score = score_repo(repo_path)

        projects.append({
            'name': name,
            'description': description,
            'score': score,
            'path': str(repo_path)
        })

    if not projects:
        print("Error: No valid repositories found", file=sys.stderr)
        sys.exit(1)

    output_path = build_html(projects, args.output, args.title)
    print(f"Generated showcase: {output_path}")
    print(f"Projects: {len(projects)}")
    for p in sorted(projects, key=lambda x: x['score'], reverse=True):
        print(f"  {p['name']:30} {p['score']:3}/100")


if __name__ == '__main__':
    main()
