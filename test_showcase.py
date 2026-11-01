#!/usr/bin/env python3
"""Tests for buildshowcase."""

import unittest
import os
import shutil
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
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

    def test_build_html_replaces_output_symlink_without_following_it(self):
        output_path = self.temp_dir / 'linked-output.html'
        outside_path = self.temp_dir / 'outside-output.html'
        outside_path.write_text('do not overwrite')
        try:
            os.symlink(str(outside_path), str(output_path))
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'symlinks unavailable: {error}')

        showcase.build_html([{
            'name': 'Safe output',
            'description': 'Project',
            'score': 50,
        }], output_path)

        self.assertFalse(output_path.is_symlink())
        self.assertEqual(outside_path.read_text(), 'do not overwrite')
        self.assertIn('<!DOCTYPE html>', output_path.read_text())

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

    def test_score_breakdown_detects_files_ending_in_test(self):
        repo_path = self.temp_dir / 'pattern-repo'
        repo_path.mkdir()
        (repo_path / 'feature_test.py').write_text('assert True\n')

        breakdown = showcase.score_breakdown(repo_path)

        self.assertEqual(breakdown['tests'], 10)

    def test_scan_repo_ignores_symlinked_readmes_and_screenshots(self):
        repo_path = self.temp_dir / 'symlink-repo'
        repo_path.mkdir()
        outside_readme = self.temp_dir / 'outside.txt'
        outside_readme.write_text('private content')
        outside_image = self.temp_dir / 'outside.png'
        outside_image.write_bytes(b'private image')
        screenshot_dir = repo_path / 'screenshots'
        screenshot_dir.mkdir()

        try:
            os.symlink(str(outside_readme), str(repo_path / 'README.md'))
            os.symlink(str(outside_image), str(screenshot_dir / 'preview.png'))
        except (OSError, NotImplementedError) as error:
            self.skipTest(f'symlinks unavailable: {error}')

        project = showcase.scan_repo(repo_path)

        self.assertEqual(project['description'], 'No description available')
        self.assertEqual(project['breakdown']['documentation'], 0)
        self.assertEqual(project['screenshots'], [])

    def test_build_html_rejects_screenshot_outside_project_root(self):
        repo_path = self.temp_dir / 'bounded-repo'
        repo_path.mkdir()
        outside_image = self.temp_dir / 'outside.png'
        outside_image.write_bytes(b'private image')
        output_path = self.temp_dir / 'bounded.html'

        showcase.build_html([{
            'name': 'Bounded',
            'description': 'Project',
            'score': 50,
            'path': str(repo_path),
            'screenshots': [outside_image],
        }], output_path)

        self.assertNotIn('<img ', output_path.read_text())

    def test_large_readmes_and_screenshots_are_not_loaded(self):
        repo_path = self.temp_dir / 'large-files'
        repo_path.mkdir()
        (repo_path / 'README.md').write_text('12345')
        screenshot_dir = repo_path / 'screenshots'
        screenshot_dir.mkdir()
        (screenshot_dir / 'preview.png').write_bytes(b'12345')

        with patch.object(showcase, 'MAX_README_BYTES', 4), patch.object(
            showcase, 'MAX_SCREENSHOT_BYTES', 4
        ):
            project = showcase.scan_repo(repo_path)
            output_path = self.temp_dir / 'large-files.html'
            showcase.build_html([project], output_path)

        self.assertEqual(project['description'], 'No description available')
        self.assertNotIn('<img ', output_path.read_text())

    def test_find_screenshots_with_negative_limit_returns_none(self):
        repo_path = self.temp_dir / 'limited-repo'
        repo_path.mkdir()
        screenshot_dir = repo_path / 'screenshots'
        screenshot_dir.mkdir()
        (screenshot_dir / 'preview.png').write_bytes(b'image')

        self.assertEqual(showcase.find_screenshots(repo_path, -1), [])

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

    def test_build_html_tolerates_malformed_score_data(self):
        output_path = self.temp_dir / 'malformed.html'

        showcase.build_html([{
            'name': 'Malformed',
            'description': 'Project',
            'score': 'not a score',
            'breakdown': None,
        }], output_path)

        html = output_path.read_text()
        self.assertIn('Score: 0/100', html)
        self.assertIn('Tests: 0/25', html)

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

    def test_main_uses_fallback_when_readme_cannot_be_read(self):
        repo_path = self.temp_dir / 'unreadable-readme'
        repo_path.mkdir()
        readme = repo_path / 'README.md'
        readme.write_text('# Repo\n\nDescription.')
        output_path = self.temp_dir / 'fallback.html'
        original_read_bounded_bytes = showcase._read_bounded_bytes

        def read_bounded_bytes(path, *args, **kwargs):
            if path == readme:
                raise OSError('read failed')
            return original_read_bounded_bytes(path, *args, **kwargs)

        with patch.object(showcase, '_read_bounded_bytes', new=read_bounded_bytes):
            result = showcase.main([str(repo_path), '--output', str(output_path)])

        self.assertEqual(result, 0)
        self.assertIn('No description available', output_path.read_text())

    def test_main_skips_repository_when_scanning_fails(self):
        repo_path = self.temp_dir / 'unreadable-repo'
        repo_path.mkdir()
        output = StringIO()

        with patch.object(showcase, 'scan_repo', side_effect=OSError('read failed')):
            with redirect_stderr(output):
                result = showcase.main([str(repo_path)])

        self.assertEqual(result, 1)
        self.assertIn('could not read', output.getvalue())

    def test_main_reports_only_embedded_screenshots(self):
        repo_path = self.temp_dir / 'broken-screenshot'
        repo_path.mkdir()
        (repo_path / 'README.md').write_text('# Repo\n\nDescription.')
        screenshot_dir = repo_path / 'screenshots'
        screenshot_dir.mkdir()
        screenshot = screenshot_dir / 'preview.png'
        screenshot.write_bytes(b'fake image')
        output_path = self.temp_dir / 'broken-screenshot.html'
        stdout = StringIO()

        with patch.object(showcase, '_image_data_uri', side_effect=OSError('read failed')):
            with redirect_stdout(stdout):
                result = showcase.main([str(repo_path), '--output', str(output_path)])

        self.assertEqual(result, 0)
        self.assertNotIn('screenshots:', stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
