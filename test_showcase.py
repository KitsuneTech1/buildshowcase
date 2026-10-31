#!/usr/bin/env python3
"""Tests for buildshowcase."""

import unittest
import tempfile
from pathlib import Path
import showcase


class TestShowcase(unittest.TestCase):
    """Test showcase functionality."""

    def setUp(self):
        """Create sample repositories."""
        self.temp_dir = Path(tempfile.mkdtemp())

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


if __name__ == '__main__':
    unittest.main()
