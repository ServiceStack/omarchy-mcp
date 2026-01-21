# Omarchy MCP

A Model Context Protocol (MCP) server for integrating [Omarchy](https://omarchy.sh) desktop environment theme management with AI assistants like Claude.

## Overview

Omarchy MCP enables AI assistants to manage themes in Omarchy - a Linux desktop environment that supports extensive theme customization including color schemes, backgrounds, and UI elements.

With this MCP server, AI assistants can:
- List available themes (built-in and custom/extra themes)
- Switch between installed themes
- Preview theme images before applying them
- Install new themes from GitHub repositories
- Uninstall themes
- Rotate background images
- Query the currently active theme

## Installation

### From PyPI

```bash
pip install omarchy-mcp
```

### From Source

```bash
git clone https://github.com/ServiceStack/omarchy-mcp.git
cd omarchy-mcp
pip install -e .
```

## Configuration

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "omarchy": {
      "description": "Manage Omarchy Desktop Themes",
      "command": "uvx",
      "args": [
        "omarchy-mcp"
      ]
    }
  }
}
```

### Using in llms .py

Or paste server configuration into [llms .py MCP Servers](https://llmspy.org/docs/extensions/fast_mcp):

Name: `omarchy-mcp`

```json
{
  "description": "Manage Omarchy Desktop Themes",
  "command": "uvx",
  "args": [
    "omarchy-mcp"
  ]
}
```

### Development Server

For development, you can run this server using `uv`:

```json
{
  "mcpServers": {
    {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/ServiceStack/omarchy-mcp",
        "omarchy-mcp"
      ]
    }
  }
}
```

## Available Tools

### omarchy_theme_list

Lists installed Omarchy themes.

**Parameters:**
- `filter` (optional): Filter themes by type
  - `"ALL"` (default) - All installed themes
  - `"BUILT_IN"` - Only built-in themes
  - `"EXTRA"` - Only custom/extra themes

**Returns:** List of theme names, one per line

### omarchy_theme_current

Gets the currently active theme.

**Returns:** Current theme name

### omarchy_theme_set

Applies a theme to the Omarchy desktop.

**Parameters:**
- `theme` (required): Theme name to apply (supports partial/case-insensitive matching)

**Returns:** Preview image of the applied theme

### omarchy_theme_bg_next

Rotates to the next background image in the current theme.

**Returns:** The new background image

### omarchy_extra_themes_to_install

Lists available extra themes that can be installed from GitHub.

**Parameters:**
- `scheme` (optional): Filter by color scheme
  - `"DARK"` (default) - Dark themed extras
  - `"LIGHT"` - Light themed extras

**Returns:** List of installable theme names

### omarchy_preview_theme

Downloads and returns a preview image for a theme without applying it.

**Parameters:**
- `name` (required): Theme name (supports partial/case-insensitive matching)

**Returns:** Theme preview image

### omarchy_install_extra_theme

Installs a new extra/community theme from its GitHub repository.

**Parameters:**
- `name` (required): Theme name to install

**Returns:** Theme preview image after installation

### omarchy_uninstall_extra_theme

Uninstalls a previously installed extra/community theme.

**Parameters:**
- `name` (required): Theme name to uninstall

**Returns:** Status message

## Theme Matching

Theme names support flexible matching:
- **Case-insensitive**: "tokyo night", "TOKYO NIGHT", and "Tokyo Night" all match
- **Partial matching**: "tokyo" matches "Tokyo Night"
- **Punctuation-insensitive**: "tokyo-night", "tokyo_night", and "tokyonight" all match

## Requirements

- **Python**: 3.10, 3.11, or 3.12
- **Omarchy**: Must be installed on the system
- **Linux**: With Wayland display server

### Dependencies

- `fastmcp>=0.1.0` - MCP server framework
- `aiohttp` - Async HTTP client for downloading preview images

## Built-in Themes

Omarchy comes with 14 built-in themes:
- Tokyo Night
- Catppuccin
- Ethereal
- Everforest
- Gruvbox
- Hackerman
- Osaka Jade
- Kanagawa
- Nord
- Matte Black
- Ristretto
- Flexoki Light
- Rose Pine
- Catppuccin Latte

## Extra Themes

Over 100 additional community themes are available for installation, including various color schemes for both dark and light preferences.

## Development

### Setup

```bash
git clone https://github.com/ServiceStack/omarchy-mcp.git
cd omarchy-mcp
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests -v
```

### Linting and Formatting

```bash
ruff check .
ruff format .
```

### Building

```bash
python -m build
```

## License

BSD-3-Clause
