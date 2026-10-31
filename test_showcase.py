#!/usr/bin/env python3
"""Tests for buildshowcase."""

import unittest
import shutil
from pathlib import Path
import showcase


class TestShowcase(unittest.TestCase):
    """Test showcase functionality."""

    def setUp(self):
        """Create sample repositories."""
        self.temp_dir = Path(__file__).parent / '.test-tmp' / self._testMethodName
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

        # Create first repo
        repo1 = self.temp_dir / 'repo-one'
        repo1.mkdir()
        (repo1 / 'README.md').write_text('# Repo One\n\nThis is the first repo.')
        (repo1 / 'main.py').write_text('print("hello")\n' * 5)
        (repo1 / 'test_main.py').write_text('def test(): assert True\n')

        # Create second repo
        repo2 = self.temp_dir / 'repo-two'
        repo2.mkdir()
        (repo2 / 'README.md').write_text('# Repo Two\n\nThis is the second repo.')
        (repo2 / 'main.py').write_text('print("hello")\n' * 3)
        (repo2 / 'package.json').write_text('{"name":"repo-two"}')

    def test_get_repo_name(self):
        """Test extracting repo name."""
        repo_path = self.temp_dir / 'repo-one'
        name = showcase.get_repo_name(repo_path)
        self.assertEqual(name, 'repo-one')

    def test_get_repo_name_handles_current_directory(self):
        self.assertEqual(showcase.get_repo_name('.'), Path.cwd().name)

    def test_get_repo_description(self):
        """Test extracting description from README."""
        repo_path = self.temp_dir / 'repo-one'
        desc = showcase.get_repo_description(repo_path)
        self.assertIn('first repo', desc)

    def test_score_repo(self):
        """Test scoring a repository."""
        repo_path = self.temp_dir / 'repo-one'
        score = showcase.score_repo(repo_path)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_score_repo_with_deps(self):
        """Test that repos with dependencies get higher scores."""
        repo_with_deps = self.temp_dir / 'repo-with-deps'
        repo_with_deps.mkdir()
        (repo_with_deps / 'README.md').write_text('# Test')
        (repo_with_deps / 'main.py').write_text('x=1')
        (repo_with_deps / 'package.json').write_text('{}')

        repo_without_deps = self.temp_dir / 'repo-no-deps'
        repo_without_deps.mkdir()
        (repo_without_deps / 'README.md').write_text('# Test')
        (repo_without_deps / 'main.py').write_text('x=1')

        score_with = showcase.score_repo(repo_with_deps)
        score_without = showcase.score_repo(repo_without_deps)

        self.assertGreater(score_with, score_without)

    def test_score_can_reach_100(self):
        repo_path = self.temp_dir / 'complete-repo'
        repo_path.mkdir()
        (repo_path / 'README.md').write_text('# Complete')
        (repo_path / 'docs').mkdir()
        (repo_path / 'pyproject.toml').write_text('[project]\nname = "complete"\n')
        for index in range(3):
            test_dir = repo_path / f'tests-{index}'
            test_dir.mkdir()
            (test_dir / 'test_case.py').write_text('assert True\n')

        self.assertEqual(showcase.score_repo(repo_path), 100)

    def test_build_html(self):
        """Test HTML generation."""
        projects = [
            {
                'name': 'Test Project',
                'description': 'A test project',
                'score': 75,
                'path': '/test'
            }
        ]

        output_path = self.temp_dir / 'index.html'
        result = showcase.build_html(projects, output_path)

        self.assertTrue(output_path.exists())
        html = output_path.read_text()
        self.assertIn('Test Project', html)
        self.assertIn('75', html)
        self.assertIn('<!DOCTYPE html>', html)

    def test_build_html_sorting(self):
        """Test that projects are sorted by score."""
        projects = [
            {'name': 'Zebra', 'description': 'Low score', 'score': 50, 'path': '/low'},
            {'name': 'Apple', 'description': 'High score', 'score': 95, 'path': '/high'},
            {'name': 'Middle', 'description': 'Mid score', 'score': 70, 'path': '/mid'},
        ]

        output_path = self.temp_dir / 'index.html'
        showcase.build_html(projects, output_path)

        html = output_path.read_text()
        # Apple (95) should appear before Zebra (50)
        apple_idx = html.find('Apple')
        zebra_idx = html.find('Zebra')
        self.assertGreater(zebra_idx, apple_idx)

    def test_build_html_uses_name_as_tie_breaker(self):
        output_path = self.temp_dir / 'tie.html'
        showcase.build_html([
            {'name': 'Zebra', 'description': 'Later', 'score': 50},
            {'name': 'Apple', 'description': 'Earlier', 'score': 50},
        ], output_path)

        html = output_path.read_text()
        self.assertLess(html.find('Apple'), html.find('Zebra'))

    def test_score_breakdown_ignores_generated_directories(self):
        repo_path = self.temp_dir / 'generated-repo'
        repo_path.mkdir()
        (repo_path / 'main.py').write_text('x = 1\n')
        generated = repo_path / 'node_modules'
        generated.mkdir()
        (generated / 'generated.js').write_text('x = 1\n')
        (repo_path / 'tests').mkdir()
        (repo_path / 'tests' / 'test_main.py').write_text('assert True\n')

        breakdown = showcase.score_breakdown(repo_path)

        self.assertEqual(breakdown['size'], 25)
        self.assertEqual(breakdown['tests'], 10)

    def test_scan_repo_finds_screenshots_and_builds_self_contained_html(self):
        repo_path = self.temp_dir / 'visual-repo'
        repo_path.mkdir()
        (repo_path / 'README.md').write_text('# Visual repo\n\nA visual project.')
        screenshot_dir = repo_path / 'screenshots'
        screenshot_dir.mkdir()
        (screenshot_dir / 'home.png').write_bytes(b'fake png bytes')

        project = showcase.scan_repo(repo_path)
        output_path = self.temp_dir / 'nested' / 'portfolio.html'
        showcase.build_html([project], output_path, '<Portfolio>')

        html = output_path.read_text()
        self.assertEqual(project['screenshots'], [screenshot_dir / 'home.png'])
        self.assertIn('data:image/png;base64,ZmFrZSBwbmcgYnl0ZXM=', html)
        self.assertIn('&lt;Portfolio&gt;', html)
        self.assertNotIn(str(repo_path), html)

    def test_build_html_escapes_untrusted_project_text(self):
        output_path = self.temp_dir / 'escaped.html'
        showcase.build_html([
            {'name': '<script>alert(1)</script>', 'description': 'A & B', 'score': 50}
        ], output_path)

        html = output_path.read_text()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('A &amp; B', html)

    def test_main_skips_invalid_repositories_and_writes_output(self):
        repo_path = self.temp_dir / 'valid-repo'
        repo_path.mkdir()
        (repo_path / 'README.md').write_text('# Valid\n\nWorks.')
        output_path = self.temp_dir / 'cli-output.html'

        result = showcase.main([str(self.temp_dir / 'missing'), str(repo_path), '--output', str(output_path)])

        self.assertEqual(result, 0)
        self.assertTrue(output_path.exists())

    def test_main_returns_one_when_all_repositories_are_invalid(self):
        result = showcase.main([str(self.temp_dir / 'missing')])

        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()
