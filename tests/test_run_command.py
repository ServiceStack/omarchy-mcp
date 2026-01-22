"""Test run_command helper."""

import asyncio
import sys

sys.path.insert(0, "src")

import pytest
from omarchy_mcp.server import run_command


@pytest.mark.asyncio
async def test_omarchy_theme_list():
    """Test that run_command returns full output from omarchy-theme-list."""
    stdout, stderr = await run_command("omarchy-theme-list")

    print("=== STDOUT ===")
    print(repr(stdout))
    print()
    print("=== STDOUT (raw) ===")
    print(stdout)
    print()
    print("=== STDERR ===")
    print(repr(stderr))
    print()
    print(f"=== Line count: {len(stdout.splitlines())} ===")


if __name__ == "__main__":
    asyncio.run(test_omarchy_theme_list())
