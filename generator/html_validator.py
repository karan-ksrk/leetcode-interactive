"""HTML validation for generated problem pages."""

from dataclasses import dataclass, field
from pathlib import Path
from html.parser import HTMLParser
import re

HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    pass


@dataclass
class ValidationResult:
    """Result of HTML validation."""
    passed: bool
    static_checks: dict = field(default_factory=dict)
    dynamic_checks: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def _check_html_structure(html_content: str) -> dict:
    """Check basic HTML structure (no errors on parse)."""
    checks = {}

    try:
        parser = HTMLParser()
        parser.feed(html_content)
        checks["parses"] = True
    except Exception as e:
        checks["parses"] = False
        return checks

    # Check for required functions/elements
    checks["has_build_function"] = bool(re.search(r'function\s+build\s*\(|const\s+build\s*=', html_content))
    checks["has_show_function"] = bool(re.search(r'function\s+show\s*\(|const\s+show\s*=', html_content))
    checks["has_preset_selector"] = bool(re.search(r'data-preset|class=["\'].*preset', html_content))
    checks["has_controls"] = bool(re.search(r'play|next|back|restart|scrubber', html_content, re.IGNORECASE))
    checks["has_scrubber"] = bool(re.search(r'input.*type=["\']range', html_content))
    checks["has_keydown_handler"] = bool(re.search(r'keydown|keypress|key.*event', html_content, re.IGNORECASE))
    checks["has_prefers_reduced_motion"] = bool(re.search(r'prefers-reduced-motion', html_content))
    checks["has_aria_live"] = bool(re.search(r'aria-live', html_content))
    checks["has_console_assert"] = bool(re.search(r'console\.assert', html_content))

    return checks


def validate(html_path: Path, run_dynamic: bool = True) -> ValidationResult:
    """Validate an HTML file (static checks always, dynamic optional)."""
    html_path = Path(html_path)
    result = ValidationResult()

    # Check file exists and is non-empty
    if not html_path.exists():
        result.errors.append(f"File does not exist: {html_path}")
        return result

    if html_path.stat().st_size == 0:
        result.errors.append("File is empty")
        return result

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        result.errors.append(f"Cannot read file: {e}")
        return result

    # Static checks
    result.static_checks = _check_html_structure(html_content)

    # Check all required functions/elements are present
    required_checks = [
        "parses",
        "has_build_function",
        "has_show_function",
        "has_preset_selector",
        "has_controls",
        "has_scrubber",
        "has_keydown_handler",
        "has_prefers_reduced_motion",
        "has_aria_live",
        "has_console_assert",
    ]

    for check_name in required_checks:
        if check_name not in result.static_checks or not result.static_checks[check_name]:
            result.errors.append(f"Static check failed: {check_name}")

    # Dynamic checks (optional, requires Playwright)
    if run_dynamic and HAS_PLAYWRIGHT:
        result.dynamic_checks = _run_dynamic_checks(html_path)
        for key, value in result.dynamic_checks.items():
            if not value.get("passed", False):
                result.errors.append(f"Dynamic check failed: {key} - {value.get('error', 'unknown')}")

    result.passed = len(result.errors) == 0
    return result


def _run_dynamic_checks(html_path: Path) -> dict:
    """Run dynamic checks via Playwright."""
    checks = {}

    if not HAS_PLAYWRIGHT:
        return {"playwright_not_installed": {"passed": False, "error": "Playwright not installed"}}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page_errors = []
            page.on("pageerror", lambda e: page_errors.append(str(e)))

            # Navigate to HTML file
            file_url = f"file://{html_path.resolve()}"
            page.goto(file_url)

            # Check for uncaught errors
            checks["no_page_errors"] = {
                "passed": len(page_errors) == 0,
                "error": f"Page errors: {page_errors}" if page_errors else None,
            }

            # Try clicking play button (if exists)
            try:
                play_btn = page.locator("button:has-text('Play'), button:has-text('play'), [data-action='play']")
                if play_btn.is_visible():
                    play_btn.click()
                    page.wait_for_timeout(500)
                checks["play_button_works"] = {"passed": True}
            except Exception as e:
                checks["play_button_works"] = {"passed": False, "error": str(e)}

            # Try clicking next (if exists)
            try:
                next_btn = page.locator("button:has-text('Next'), button:has-text('next'), [data-action='next']")
                if next_btn.is_visible():
                    next_btn.click()
                    page.wait_for_timeout(500)
                checks["next_button_works"] = {"passed": True}
            except Exception as e:
                checks["next_button_works"] = {"passed": False, "error": str(e)}

            # Collect console errors
            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            checks["no_console_errors"] = {
                "passed": len(console_errors) == 0,
                "error": f"Console errors: {console_errors}" if console_errors else None,
            }

            browser.close()

    except Exception as e:
        checks["playwright_error"] = {"passed": False, "error": str(e)}

    return checks
