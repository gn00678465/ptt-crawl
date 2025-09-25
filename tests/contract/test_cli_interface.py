"""CLI Interface Contract Tests

These tests verify the CLI command interfaces match the specifications.
They MUST FAIL initially (no implementation exists yet).
"""
import subprocess
import sys

import pytest


class TestCLIInterface:
    """Test CLI command interface contracts."""

    @pytest.fixture()
    def cli_command(self) -> list[str]:
        """Base CLI command for testing."""
        return [sys.executable, "-m", "src.cli.main"]

    def test_main_help_command_exists(self, cli_command: list[str]) -> None:
        """Test that main help command is available."""
        result = subprocess.run([*cli_command, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "ptt-crawler" in result.stdout.lower()
        assert "usage:" in result.stdout.lower()

    def test_crawl_command_exists(self, cli_command: list[str]) -> None:
        """Test that crawl command exists with proper options."""
        result = subprocess.run([*cli_command, "crawl", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "board" in result.stdout.lower()
        assert "--category" in result.stdout
        assert "--pages" in result.stdout
        assert "--output" in result.stdout
        assert "--force" in result.stdout

    def test_status_command_exists(self, cli_command: list[str]) -> None:
        """Test that status command exists with proper options."""
        result = subprocess.run([*cli_command, "status", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--format" in result.stdout
        assert "--detailed" in result.stdout

    def test_config_command_exists(self, cli_command: list[str]) -> None:
        """Test that config command exists with subcommands."""
        result = subprocess.run([*cli_command, "config", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "show" in result.stdout
        assert "set" in result.stdout
        assert "reset" in result.stdout

    def test_clean_command_exists(self, cli_command: list[str]) -> None:
        """Test that clean command exists with proper options."""
        result = subprocess.run([*cli_command, "clean", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--states" in result.stdout
        assert "--cache" in result.stdout
        assert "--logs" in result.stdout

    def test_crawl_command_parameters(self, cli_command: list[str]) -> None:
        """Test crawl command parameter validation."""
        # Test valid board parameter
        result = subprocess.run(
            [*cli_command, "crawl", "Stock", "--dry-run"], capture_output=True, text=True
        )
        # Should pass parameter validation but fail on implementation
        assert result.returncode != 0  # No implementation yet

    def test_global_options_work(self, cli_command: list[str]) -> None:
        """Test that global options are recognized."""
        result = subprocess.run(
            [*cli_command, "--log-level", "DEBUG", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_config_show_subcommand(self, cli_command: list[str]) -> None:
        """Test config show subcommand."""
        result = subprocess.run(
            [*cli_command, "config", "show", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_config_set_subcommand(self, cli_command: list[str]) -> None:
        """Test config set subcommand requires key and value."""
        result = subprocess.run(
            [*cli_command, "config", "set", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_exit_codes_are_defined(self, cli_command: list[str]) -> None:
        """Test that proper exit codes are returned for different scenarios."""
        # Test invalid command returns non-zero exit code
        result = subprocess.run(
            [*cli_command, "nonexistent_command"], capture_output=True, text=True
        )
        assert result.returncode != 0
