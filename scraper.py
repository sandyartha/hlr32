#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper_nodriver_final.py
Robust nodriver-based title scraper with:
- auto-detect Chromium binary
- Xvfb fallback when DISPLAY missing
- --no-sandbox and recommended browser args for CI/root
- retries and requests fallback (browser-like headers)
- saves result to result.txt
"""

import os
import sys
import time
import subprocess
import traceback
import asyncio
from typing import Optional

import requests
from bs4 import BeautifulSoup

# nodriver import deferred (some CI may not have it installed)
try:
    import nodriver as uc
except Exception:
    uc = None

URL = "https://www.nowsecure.nl"
RESULT_FILE = "result.txt"

# Common chromium binary locations on Linux runners
CHROME_CANDIDATES = [
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/snap/bin/chromium",
]


def detect_chrome_path() -> Optional[str]:
    for p in CHROME_CANDIDATES:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    # try 'which'
    try:
        which_out = subprocess.check_output(["which", "chromium-browser"], stderr=subprocess.DEVNULL).decode().strip()
        if which_out:
            return which_out
    except Exception:
        pass
    # not found
    return None


def ensure_xvfb_display() -> None:
    """
    If DISPLAY not set, try start Xvfb on :99 and export DISPLAY.
    Non-blocking start; user should ensure Xvfb installed in environment.
    """
    if os.environ.get("DISPLAY"):
        print(f"DISPLAY present: {os.environ['DISPLAY']}")
        return

    # try starting Xvfb
    print("🧩 DISPLAY not set — attempting to start Xvfb :99")
    try:
        # Start Xvfb in background
        subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.environ["DISPLAY"] = ":99"
        # small delay to let Xvfb initialize
        time.sleep(1.5)
        print("✅ Xvfb started, DISPLAY=:99")
    except FileNotFoundError:
        print("⚠️ Xvfb not installed or not in PATH. Please install Xvfb or run with headless browser options.")
    except Exception as e:
        print("⚠️ Failed to start Xvfb:", e)


def save_result(url: str, title: Optional[str]) -> None:
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{url} -> {repr(title)}\n")
    print(f"Saved result to {RESULT_FILE}")


def get_title_requests(url: str) -> Optional[str]:
    """
    Fallback HTTP GET using requests with browser-like headers.
    Some sites with heavy anti-bot may still block this.
    """
    print("🌐 Fallback: attempting requests with browser-like headers...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    cookies = {"consent": "true"}  # small dummy cookie; can be extended if needed
    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
            print("✅ Requests fallback found title:", title)
            return title
        else:
            print("⚠️ Requests fallback: no <title> found in HTML")
            return None
    except Exception as e:
        print("❌ Requests fallback failed:", e)
        return None


async def get_title_nodriver(url: str, chrome_path: Optional[str] = None, max_retries: int = 2) -> Optional[str]:
    """
    Attempt to start nodriver and fetch document.title via page.evaluate('document.title')
    Returns title or None.
    """
    if uc is None:
        print("⚠️ nodriver not installed in this environment (nodriver import failed).")
        return None

    # ensure display (Xvfb) if absent
    ensure_xvfb_display()

    # find chrome if not provided
    if chrome_path is None:
        chrome_path = detect_chrome_path()
        if chrome_path:
            print(f"🔎 Detected chromium binary: {chrome_path}")
        else:
            print("🔎 Chromium binary not detected. nodriver may still attempt to find a browser but it's recommended to install chromium.")
    else:
        print(f"🔎 Using provided chromium binary: {chrome_path}")

    # recommended browser args for CI/root/headless
    browser_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-popup-blocking",
        "--disable-setuid-sandbox",
        "--remote-debugging-pipe",
        "--disable-blink-features=AutomationControlled",
        # "--headless=new"  # nodriver will manage headless via its headless param; commented to avoid compatibility issues
    ]

    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        try:
            print(f"🚀 nodriver start attempt {attempt}/{max_retries + 1} ...")
            # call uc.start with args directly (Config.browser_args is not a setter)
            if chrome_path:
                browser = await uc.start(
                    browser_executable_path=chrome_path,
                    headless=True,
                    no_sandbox=True,
                    browser_args=browser_args,
                )
            else:
                browser = await uc.start(
                    headless=True,
                    no_sandbox=True,
                    browser_args=browser_args,
                )

            # open page
            page = await browser.get(url)

            # wait for up to ~6s for a title to appear (poll)
            title = None
            for _ in range(12):
                try:
                    # some versions support page.title() - but use evaluate for max compatibility
                    title = await page.evaluate("document.title")
                except Exception:
                    title = None
                if title:
                    break
                await asyncio.sleep(0.5)

            # try to save cookies if supported (best-effort)
            try:
                cookies_obj = getattr(browser, "cookies", None)
                if cookies_obj:
                    save_fn = getattr(cookies_obj, "save", None)
                    if callable(save_fn):
                        try:
                            save_fn("nodriver_cookies.json")
                            print("💾 Saved cookies to nodriver_cookies.json")
                        except Exception:
                            # ignore save errors
                            pass
            except Exception:
                pass

            # proper cleanup: browser.stop() is synchronous per nodriver notes
            try:
                browser.stop()
            except Exception:
                # fallback to attribute-based close
                close_fn = getattr(browser, "close", None)
                if callable(close_fn):
                    try:
                        await close_fn()
                    except Exception:
                        pass

            if title:
                print("✅ nodriver fetched title:", title)
                return title
            else:
                print("⚠️ nodriver did not find a title (empty). Retrying...")
        except Exception as e:
            print("❌ nodriver failed on attempt", attempt, ":", e)
            # print trace for debugging
            traceback.print_exc()
            # If it's the last attempt, break and fallback
            if attempt > max_retries:
                print("❌ Reached max nodriver attempts, will fallback to requests.")
                break
            # small backoff
            await asyncio.sleep(1.0 + attempt * 0.5)
            continue

    return None


async def main():
    url = URL
    title = None

    # 1) try nodriver first (if installed)
    title = await get_title_nodriver(url)
    # 2) fallback to requests if nodriver fails
    if not title:
        title = get_title_requests(url)

    print("🎯 Final result:", title)
    save_result(url, title)


if __name__ == "__main__":
    # nodriver's author historically used uc.loop().run_until_complete
    # if nodriver is present, use its loop helper to be compatible; otherwise fallback to asyncio.run
    if uc is not None and hasattr(uc, "loop"):
        try:
            uc.loop().run_until_complete(main())
        except Exception:
            # final fallback to asyncio.run
            asyncio.run(main())
    else:
        asyncio.run(main())
