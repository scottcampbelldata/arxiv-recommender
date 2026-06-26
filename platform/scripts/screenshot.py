"""Capture demo screenshots for the case study (desktop + mobile)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARXREC_SCREENSHOT_URL", "http://127.0.0.1:3000")
OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)


def shoot() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_d = browser.new_context(viewport={"width": 1440, "height": 980}, device_scale_factor=2)
        page = ctx_d.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        try:
            page.wait_for_selector("article", timeout=60_000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(3500)
        page.screenshot(path=str(OUT / "demo-desktop.png"), full_page=True)
        print("wrote", OUT / "demo-desktop.png")
        ctx_d.close()

        ctx_m = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15"
            ),
        )
        page = ctx_m.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60_000)
        try:
            page.wait_for_selector("article", timeout=60_000)
        except Exception:  # noqa: BLE001
            pass
        page.wait_for_timeout(3500)
        page.screenshot(path=str(OUT / "demo-mobile.png"), full_page=True)
        print("wrote", OUT / "demo-mobile.png")
        ctx_m.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(shoot())
