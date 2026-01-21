"""MCP Server for Omarchy."""

import asyncio
import aiohttp
import os
import json

from enum import StrEnum
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from google import genai
from google.genai import types
from fastmcp import FastMCP
from fastmcp.utilities.types import Image

# Load omarchy themes from JSON file on startup
_themes_file = Path(__file__).parent / "omarchy_themes.json"
with open(_themes_file, "r") as f:
    OMARCHY_THEMES = json.load(f)

OMARCHY_PATH = os.environ.get("OMARCHY_PATH", os.path.expanduser("~/.local/share/omarchy"))

# Initialize FastMCP server
mcp = FastMCP("omarchy-mcp")

ColorScheme = StrEnum("ColorScheme", ["LIGHT", "DARK"])

ThemeFilter = StrEnum("ThemeFilter", ["ALL", "BUILT_IN", "EXTRA"])

def _get_env() -> dict[str, str]:
    """Get environment with OMARCHY_PATH, HOME, and Wayland session vars set."""
    env = os.environ.copy()
    if "HOME" not in env:
        env["HOME"] = os.path.expanduser("~")
    if "OMARCHY_PATH" not in env:
        env["OMARCHY_PATH"] = os.path.expanduser("~/.local/share/omarchy")

    # Ensure Wayland/session environment variables are set for GUI apps like swaybg
    wayland_env_vars = {
        "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}",
        "WAYLAND_DISPLAY": "wayland-1",
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path=/run/user/{os.getuid()}/bus",
    }
    for key, default in wayland_env_vars.items():
        if key not in env:
            env[key] = default

    return env

async def run_command(*args: str) -> tuple[str, str]:
    """Run a command and return (stdout, stderr) as UTF-8 strings.

    Raises RuntimeError if the command fails (non-zero exit code).
    """
    env = _get_env()
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=os.path.expanduser("~")
    )
    stdout, stderr = await process.communicate()
    stdout_str = stdout.decode("utf-8") if stdout else ""
    stderr_str = stderr.decode("utf-8") if stderr else ""
    if process.returncode != 0:
        raise RuntimeError(f"Command {args[0]} failed: {stderr_str}")
    return stdout_str, stderr_str

def sanitize(name: str) -> str:
    return name.replace(" ", "").replace("_", "").replace("-", "").lower()

def get_theme_by_name(name: str) -> Optional[dict]:
    """Get theme dict from OMARCHY_THEMES by name (case-insensitive, partial match)."""
    sanitized_name = sanitize(name)
    ret = next((t for t in OMARCHY_THEMES if sanitized_name in sanitize(t["name"])), None)
    if not ret:
        raise ValueError(f"Theme '{name}' not found in available themes.")
    return ret

async def get_theme_preview_image(theme_info) -> Optional[Image]:
    if theme_info and "preview_url" in theme_info:
        preview_url = theme_info["preview_url"]
        # download the image from the URL
        async with aiohttp.ClientSession() as session:
            async with session.get(preview_url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download preview image from {preview_url}")
                img_data = await resp.read()
                format = preview_url.split(".")[-1].lower() or "png"
                return Image(data=img_data, format=format)


async def get_installed_themes() -> list[str]:
    """Get a list of installed Omarchy themes."""
    stdout, _ = await run_command(f"{OMARCHY_PATH}/bin/omarchy-theme-list")
    return stdout.strip().splitlines()

def get_installed_extra_themes() -> list[str]:
    """Get a list of installed Omarchy extra themes (not symlinks)."""
    omarchy_themes = Path.home() / ".config/omarchy/themes"
    if not omarchy_themes.exists():
        return []
    installed_theme_names = [
        d.name for d in omarchy_themes.iterdir()
        if d.is_dir() and not d.is_symlink()
    ]
    return installed_theme_names

@mcp.tool()
async def omarchy_theme_list(filter: ThemeFilter = ThemeFilter.ALL) -> str:
    """Get a list of Omarchy themes."""

    stdout, _ = await run_command("omarchy-theme-current")
    current_theme = stdout.strip()
    all_installed_themes = await get_installed_themes()
    installed_extra_themes = get_installed_extra_themes()

    def render_themes(themes: list[str]) -> list[str]:
        rendered = []
        for theme in themes:
            prefix = "* " if theme == current_theme else "  "
            rendered.append(f"{prefix}{theme}")
        return rendered

    if filter == ThemeFilter.EXTRA:
        return "\n".join(render_themes(installed_extra_themes))
    elif filter == ThemeFilter.BUILT_IN:
        # sanitize by excluding extra themes
        built_in_themes = []
        sanitized_extra_themes = {sanitize(t) for t in installed_extra_themes}
        for theme in all_installed_themes:
            if sanitize(theme) not in sanitized_extra_themes:
                built_in_themes.append(theme)
        return "\n".join(render_themes(built_in_themes))
        
    # All themes
    return "\n".join(render_themes(all_installed_themes))


@mcp.tool()
async def omarchy_theme_current() -> str:
    """Get the current Omarchy theme."""
    stdout, _ = await run_command("omarchy-theme-current")
    return stdout.strip()

@mcp.tool()
async def omarchy_theme_set(theme: str) -> Optional[Image]:
    """Set the current Omarchy theme."""
    omarchy_theme = get_theme_by_name(theme)
    name = omarchy_theme["name"]

    current_theme, _ = await run_command("omarchy-theme-current")

    stdout, stderr = await run_command("omarchy-theme-set", name)

    new_theme, _ = await run_command("omarchy-theme-current")

    if current_theme is new_theme and stderr:
        raise RuntimeError(f"Failed to set theme '{name}': {stderr}")

    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_theme_bg_next() -> Image:
    """Switch to the next Omarchy theme background."""
    stdout, _ = await run_command("omarchy-theme-bg-next")
    current_background_link = Path.home() / ".config/omarchy/current/background"
    if current_background_link.is_symlink():
        current_bg = current_background_link.resolve()
        if current_bg.is_file():
            img_data = current_bg.read_bytes()
            fmt = current_bg.suffix.lower().lstrip(".")
            return Image(data=img_data, format=fmt or "png")
    return None

@mcp.tool()
async def omarchy_extra_themes_to_install(scheme: ColorScheme = ColorScheme.DARK) -> str:
    """Get a list of available Omarchy themes to install."""
    stdout, _ = await run_command("omarchy-theme-list")
    installed_themes = set(stdout.strip().splitlines())

    # Filter themes by scheme and get names not already installed
    scheme_str = scheme.value.capitalize()  # "DARK" -> "Dark", "LIGHT" -> "Light"
    available_names = {
        t["name"] for t in OMARCHY_THEMES
        if t.get("scheme") == scheme_str and t["name"] not in installed_themes
    }

    return "\n".join(sorted(available_names))

@mcp.tool()
async def omarchy_preview_theme(name:str) -> Optional[Image]:
    """Get a preview image for an Omarchy theme by name."""
    omarchy_theme = get_theme_by_name(name)
    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_install_extra_theme(name:str) -> Optional[Image]:
    """Install an Omarchy theme by name."""
    omarchy_theme = get_theme_by_name(name)

    installed_themes = await get_installed_themes()
    if omarchy_theme["name"] in installed_themes:
        raise RuntimeError(f"Theme '{name}' is already installed.")

    github_url = omarchy_theme.get("github_url")
    if not github_url:
        raise RuntimeError(f"Theme '{name}' does not have a GitHub URL for installation.")    
    
    current_theme, _ = await run_command("omarchy-theme-current")

    stdout, stderr = await run_command("omarchy-theme-install", github_url)

    new_theme, _ = await run_command("omarchy-theme-current")

    if current_theme is new_theme and stderr:
        raise RuntimeError(f"Failed to install theme '{name}': {stderr}")

    # After installation, get the theme preview image
    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_uninstall_extra_theme(name:str) -> str:
    """Uninstall an Omarchy theme by name."""

    installed_theme_names = get_installed_extra_themes()
    
    uninstall_theme = name if name in installed_theme_names else None

    # Try to match sanitized names if exact name not found
    if name not in installed_theme_names:
        omarchy_theme = get_theme_by_name(name)

        for installed_name in installed_theme_names:
            if sanitize(omarchy_theme["name"]) == sanitize(installed_name) or sanitize(name) in sanitize(installed_name):
                uninstall_theme = installed_name
                break

    if not uninstall_theme:
        return f"Theme '{name}' is not an installed extra theme:\n" + f" {'\n  '.join(installed_theme_names)}"

    stdout, stderr = await run_command("omarchy-theme-remove", uninstall_theme)

    if stderr:
        return stderr
    return stdout.strip() or "OK"


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
