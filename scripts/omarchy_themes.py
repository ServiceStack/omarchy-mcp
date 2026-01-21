#!/usr/bin/env python3
"""Generate omarchy-themes.json file containing list of theme names, github urls and preview image urls."""

import json
import re
import urllib.request
from pathlib import Path

THEMES_URL = "https://learn.omacom.io/2/the-omarchy-manual/52/themes"
EXTRA_THEMES_URL = "https://learn.omacom.io/2/the-omarchy-manual/90/extra-themes"
BASE_URL = "https://learn.omacom.io"
OUTPUT_FILE = Path(__file__).parent.parent / "src" / "omarchy_mcp" / "omarchy_themes.json"

LIGHT_THEMES = [
    # themes
    "Kanagawa","Flexoki Light", "Rose Pine", "Catppuccin Latte", 
    # extra themes
    "Bauhaus", "Black Arch", "Bliss", "The Greek", "Gruvu", "Map Quest", "Milky Matcha", "Rose of Dune", "Snow", 
    "Solarized Light", "White Gold"
]

def fetch_html(url: str) -> str:
    """Fetch HTML content from URL."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def extract_themes_section(html: str) -> str:
    """Extract the themes section between id='themes' and </main>."""
    start_match = re.search(r'id="themes"', html)
    if not start_match:
        raise ValueError("Could not find 'themes' section")

    end_match = re.search(r'</main>', html[start_match.start():])
    if not end_match:
        raise ValueError("Could not find </main> tag")

    return html[start_match.start():start_match.start() + end_match.start()]


def parse_themes(html_section: str) -> list[dict]:
    """Parse theme information from HTML section."""
    themes = []

    # Pattern to match each theme block:
    # <p><a data-action="lightbox#open:prevent" data-lightbox-target="image" data-lightbox-url-value="/u/tokyo-night-yN9jzd.png?disposition=attachment" href="/u/tokyo-night-yN9jzd.png"><img src="/u/tokyo-night-yN9jzd.png" alt="tokyo-night.png"></a>
    # <em>Tokyo Night</em></p>
    pattern = re.compile(
        r'<p>.*?<img\s+src="([^"]+)"[^>]*>.*?'
        r'<em>([^<]+)</em></p>',
        re.DOTALL
    )

    for match in pattern.finditer(html_section):
        image_url, name = match.groups()
        # Normalize relative URLs to absolute
        preview_url = image_url.strip()
        if preview_url.startswith("/"):
            preview_url = BASE_URL + preview_url
        name = name.strip()
        themes.append({
            "name": name,
            "scheme": "Dark" if name not in LIGHT_THEMES else "Light",
            "preview_url": preview_url
        })

    return themes


def extract_extra_themes_section(html: str) -> str:
    """Extract the extra themes section between id='extra-themes' and </main>."""
    start_match = re.search(r'id="extra-themes"', html)
    if not start_match:
        raise ValueError("Could not find 'extra-themes' section")

    end_match = re.search(r'</main>', html[start_match.start():])
    if not end_match:
        raise ValueError("Could not find </main> tag")

    return html[start_match.start():start_match.start() + end_match.start()]


def parse_extra_themes(html_section: str) -> list[dict]:
    """Parse theme information from HTML section."""
    themes = []

    # Pattern to match each theme block:
    # <p>...<img src="IMAGE_URL">...</p>
    # <a href="GITHUB_URL">THEME_NAME</a></p>
    pattern = re.compile(
        r'<p>.*?<img\s+src="([^"]+)"[^>]*>.*?'
        r'<a\s+href="(https://github\.com/[^"]+)">([^<]+)</a>\s*</p>',
        re.DOTALL
    )

    for match in pattern.finditer(html_section):
        image_url, github_url, name = match.groups()
        # Normalize relative URLs to absolute
        preview_url = image_url.strip()
        if preview_url.startswith("/"):
            preview_url = BASE_URL + preview_url
        name = name.strip()
        themes.append({
            "name": name,
            "scheme": "Dark" if name not in LIGHT_THEMES else "Light",
            "github_url": github_url.strip(),
            "preview_url": preview_url
        })

    return themes


def generate_themes_json() -> list[dict]:
    """Fetch themes page and generate JSON file."""
    html = fetch_html(THEMES_URL)
    themes_section = extract_themes_section(html)
    themes = parse_themes(themes_section)

    html = fetch_html(EXTRA_THEMES_URL)
    extra_themes_section = extract_extra_themes_section(html)
    extra_themes = parse_extra_themes(extra_themes_section)

    combined_themes = themes + extra_themes

    with open(OUTPUT_FILE, "w") as f:
        json.dump(combined_themes, f, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(themes)} themes and {len(extra_themes)} extra themes ({len(combined_themes)} total).")
    return combined_themes


if __name__ == "__main__":
    generate_themes_json()
