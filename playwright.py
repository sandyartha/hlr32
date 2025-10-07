#!/usr/bin/env python3
# scraper_playwright_fallback.py
import os
import asyncio
import subprocess
import time
import traceback

# nodriver optional import
try:
    import nodriver as uc
except Exception:
    uc = None

# playwright import
try:
    from playwright.async_api import async_playwright
except Exception:
    async_playwright = None

import requests
from bs4 import BeautifulSoup

URL = "https://www.nowsecure.nl"
RESULT_FILE = "result.txt"

def save_result(url, title):
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{url} -> {repr(title)}\n")
    print("Saved result to", RESULT_FILE)

def requests_title(url):
    print("🌐 Trying requests fallback (browser-like headers)...")
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/129.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        t = soup.title.string.strip() if soup.title else None
        print("✅ requests got title:", t)
        return t
    except Exception as e:
        print("❌ requests failed:", e)
        return None

async def try_nodriver(url):
    if uc is None:
        print("nodriver not installed; skipping nodriver attempt.")
        return None

    # ensure Xvfb if needed
    if os.environ.get("DISPLAY") is None:
        print("DISPLAY not found — starting Xvfb :99")
        try:
            subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.environ["DISPLAY"] = ":99"
            time.sleep(1.0)
        except Exception as e:
            print("could not start Xvfb:", e)

    chrome_candidates = ["/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome"]
    chrome_path = next((p for p in chrome_candidates if os.path.exists(p)), None)
    if chrome_path:
        print("Detected chrome:", chrome_path)
    else:
        print("Chrome not detected on system; nodriver may still try default.")

    # Extra flags often needed in CI/root
    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--remote-debugging-port=0",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=site-per-process",
    ]

    try:
        print("🚀 Starting nodriver...")
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

        page = await browser.get(url)
        # try evaluate document.title
        title = None
        for _ in range(12):
            try:
                title = await page.evaluate("document.title")
            except Exception:
                title = None
            if title:
                break
            await asyncio.sleep(0.5)

        try:
            browser.stop()
        except Exception:
            try:
                await browser.close()
            except Exception:
                pass

        print("nodriver title:", title)
        return title
    except Exception as e:
        print("nodriver failed:", e)
        traceback.print_exc()
        return None

async def try_playwright(url, proxy: str = None):
    if async_playwright is None:
        print("playwright not installed; skipping playwright attempt.")
        return None

    print("🚀 Starting Playwright (stealth-ish) ...")
    try:
        async with async_playwright() as p:
            launch_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ]
            browser = await p.chromium.launch(headless=True, args=launch_args)
            context = await browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            ))
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            await page.goto(url, timeout=60000, wait_until="load")
            title = await page.title()
            await browser.close()
            print("playwright title:", title)
            return title
    except Exception as e:
        print("playwright failed:", e)
        traceback.print_exc()
        return None

async def main():
    title = await try_nodriver(URL)
    if not title:
        # try playwright fallback
        title = await try_playwright(URL)
    if not title:
        # last resort
        title = requests_title(URL)
    print("FINAL TITLE:", title)
    save_result(URL, title)

if __name__ == "__main__":
    asyncio.run(main())
