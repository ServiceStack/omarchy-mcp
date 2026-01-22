"""MCP Server for Omarchy."""

import asyncio
import aiohttp
import os
import json

from enum import StrEnum
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP
from fastmcp.utilities.types import Image, ContentBlock
from mcp.types import ImageContent, TextContent

# Load omarchy themes from JSON file on startup
_themes_file = Path(__file__).parent / "omarchy_themes.json"
with open(_themes_file, "r") as f:
    OMARCHY_THEMES = json.load(f)

OMARCHY_PATH = os.environ.get("OMARCHY_PATH", os.path.expanduser("~/.local/share/omarchy"))

# Initialize FastMCP server
mcp = FastMCP("omarchy-mcp")

ThemeFilter = StrEnum("ThemeFilter", ["ALL", "CURRENT", "INSTALLED", "BUILT_IN", "CAN_REMOVE", "CAN_INSTALL"])

ColorScheme = StrEnum("ColorScheme", ["ANY", "LIGHT", "DARK"])

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

    stdout_str = stdout_str.strip()
    stderr_str = stderr_str.strip()

    if process.returncode != 0:
        error_msg = stderr_str or stdout_str or f"exit code {process.returncode}"
        raise RuntimeError(f"Command {args[0]} failed: {error_msg}")
    return stdout_str, stderr_str

def sanitize(name: str) -> str:
    return name.replace(" ", "").replace("_", "").replace("-", "").lower()

def matches_theme(name:str, theme_name:str) -> bool:
    """Check if name matches theme_name (case-insensitive, partial match)."""
    return sanitize(name) in sanitize(theme_name)

def get_theme_by_name(name: str) -> Optional[dict]:
    """Get theme dict from OMARCHY_THEMES by name (case-insensitive, partial match)."""
    sanitized_name = sanitize(name)
    ret = next((t for t in OMARCHY_THEMES if sanitized_name in sanitize(t["name"])), None)
    if not ret:
        raise ValueError(f"Theme '{name}' not found in available themes.")
    return ret

async def get_theme_preview_image(theme_info) -> Optional[ImageContent]:
    if theme_info and "preview_url" in theme_info:
        preview_url = theme_info["preview_url"]
        # download the image from the URL
        async with aiohttp.ClientSession() as session:
            async with session.get(preview_url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to download preview image from {preview_url}")
                img_data = await resp.read()
                format = preview_url.split(".")[-1].lower() or "png"
                return Image(data=img_data, format=format).to_image_content()


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

def text_result(text: str) -> TextContent:
    """Helper to create a TextContent result."""
    return TextContent(type="text", text=text)

@mcp.tool()
async def omarchy_theme_list(filter: ThemeFilter = ThemeFilter.INSTALLED, scheme: ColorScheme = ColorScheme.ANY) -> str:
    """Get a list of Omarchy themes."""

    stdout, _ = await run_command("omarchy-theme-current")
    current_theme = stdout.strip()
    if filter == ThemeFilter.CURRENT:
        return current_theme

    built_in_themes = []
    installed_extra_themes = get_installed_extra_themes()
    sanitized_extra_themes = {sanitize(t) for t in installed_extra_themes}
    all_installed_themes = await get_installed_themes()
    for theme in all_installed_themes:
        if sanitize(theme) not in sanitized_extra_themes:
            built_in_themes.append(theme)

    def display_themes(themes: list[str]) -> list[str]:
        rendered = []
        matching_themes = []
        for theme in themes:
            if scheme != ColorScheme.ANY:
                omarchy_theme = get_theme_by_name(theme)
                theme_scheme = omarchy_theme.get("scheme", "Any").lower()
                if theme_scheme != scheme.value.lower():
                    continue
            matching_themes.append(theme)

        max_len = max(len(t) for t in matching_themes)
        for theme in matching_themes:
            suffix = ""
            if theme == current_theme:
                suffix = " (current)"
            else:
                if theme in built_in_themes:
                    suffix = " (built-in)"
                elif theme in all_installed_themes:
                    suffix = " (installed)"
            rendered.append(f"{theme}{' ' * (max_len - len(theme))}{suffix}")
        return "\n".join(rendered)

    if filter == ThemeFilter.INSTALLED:
        return display_themes(all_installed_themes)

    if filter == ThemeFilter.CAN_REMOVE:
        return display_themes(installed_extra_themes)
    elif filter == ThemeFilter.BUILT_IN:
        # sanitize by excluding extra themes
        return display_themes(built_in_themes)
    elif filter == ThemeFilter.CAN_INSTALL:
        # Available themes are those not installed
        available_themes = []
        sanitized_installed = {sanitize(t) for t in all_installed_themes}
        for theme in OMARCHY_THEMES:
            if sanitize(theme["name"]) not in sanitized_installed:
                available_themes.append(theme["name"])
        return display_themes(available_themes)
        
    # ThemeFilter.ALL - All themes
    all_themes = [theme["name"] for theme in OMARCHY_THEMES]
    return display_themes(all_themes)

@mcp.tool()
async def omarchy_theme_set(theme: str) -> ContentBlock:
    """Set the current Omarchy theme."""
    set_theme = None
    installed_themes = await get_installed_themes()

    for t in installed_themes:
        if matches_theme(theme, t):
            set_theme = t
            break

    if not set_theme:
        return text_result(f"You need to install theme '{theme}' first before setting it.")

    omarchy_theme = get_theme_by_name(set_theme)
    name = omarchy_theme["name"]

    current_theme, _ = await run_command("omarchy-theme-current")

    if matches_theme(theme, current_theme) or matches_theme(name, current_theme):
        return text_result(f"Theme '{name}' is already the current theme.")

    stdout, stderr = await run_command("omarchy-theme-set", set_theme)

    new_theme, _ = await run_command("omarchy-theme-current")

    if current_theme == new_theme and stderr:
        return text_result(f"Failed to set theme '{name}': {stderr}")

    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_theme_bg_next() -> ImageContent | None:
    """Cycle to the next Omarchy theme background."""
    stdout, _ = await run_command("omarchy-theme-bg-next")
    current_background_link = Path.home() / ".config/omarchy/current/background"
    if current_background_link.is_symlink():
        current_bg = current_background_link.resolve()
        if current_bg.is_file():
            img_data = current_bg.read_bytes()
            fmt = current_bg.suffix.lower().lstrip(".")
            return Image(data=img_data, format=fmt or "png").to_image_content()
    return None

@mcp.tool()
async def omarchy_preview_theme(name:str) -> Optional[ImageContent]:
    """Get a preview image for an Omarchy theme by name."""
    omarchy_theme = get_theme_by_name(name)
    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_install_theme(name:str) -> Optional[ContentBlock]:
    """Install an Omarchy extra theme by name. Installing a theme automatically sets it as the current theme."""
    omarchy_theme = get_theme_by_name(name)

    installed_themes = await get_installed_themes()
    if omarchy_theme["name"] in installed_themes:
        raise RuntimeError(f"Theme '{name}' is already installed.")

    github_url = omarchy_theme.get("github_url")
    if not github_url:
        return text_result(f"Theme '{name}' does not have a GitHub URL for installation.")
    
    current_theme, _ = await run_command("omarchy-theme-current")

    stdout, stderr = await run_command("omarchy-theme-install", github_url)

    new_theme, _ = await run_command("omarchy-theme-current")

    if current_theme == new_theme and stderr:
        return text_result(f"Failed to install theme '{name}': {stderr}")

    # After installation, get the theme preview image
    return await get_theme_preview_image(omarchy_theme)

@mcp.tool()
async def omarchy_remove_theme(name:str) -> ContentBlock:
    """Uninstall an Omarchy extra theme by name. Built-in themes cannot be removed."""

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
        return text_result(f"Theme '{name}' is not an installed extra theme:\n" + f" {'\n  '.join(installed_theme_names)}")

    stdout, stderr = await run_command("omarchy-theme-remove", uninstall_theme)

    if stderr:
        return stderr
    return stdout.strip() or "OK"


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
