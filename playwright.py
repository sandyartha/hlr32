#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper_nodriver_wait_ua.py
nodriver + UA spoof + wait-until-title-changed (handles "Just a moment..." Cloudflare)
- tries nodriver first (with UA spoofing + init scripts)
- waits up to MAX_WAIT seconds for title to change from initial challenge text
- falls back to requests if nodriver fails
- saves result to result.txt
"""

import os
import time
import asyncio
import traceback

# optional imports (nodriver may not be installed in some envs)
try:
    import nodriver as uc
except Exception:
    uc = None

import requests
from bs4 import BeautifulSoup

URL = "https://www.nowsecure.nl"
RESULT_FILE = "result.txt"

# Adjust these to taste
MAX_WAIT_SECONDS = 30        # max total time to wait for challenge to pass
POLL_INTERVAL = 1.0          # seconds between title checks
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36"
)


def save_result(url: str, title: str | None):
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{url} -> {repr(title)}\n")
    print(f"Saved result to {RESULT_FILE}")


def requests_fallback(url: str) -> str | None:
    print("🌐 Requests fallback: trying browser-like headers...")
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        t = soup.title.string.strip() if soup.title else None
        print("✅ Requests fallback title:", t)
        return t
    except Exception as e:
        print("❌ Requests fallback failed:", e)
        return None


async def get_title_nodriver_wait(url: str, max_wait: int = MAX_WAIT_SECONDS) -> str | None:
    """
    Start nodriver, spoof UA, inject init script, navigate and wait until the document.title
    no longer looks like a Cloudflare "Just a moment..." challenge.
    """
    if uc is None:
        print("⚠️ nodriver not installed; skipping nodriver attempt.")
        return None

    # ensure Xvfb if running in headless CI and DISPLAY is missing (best-effort)
    if os.environ.get("DISPLAY") is None:
        try:
            # try start Xvfb in background; if not present, this will fail but we continue
            from subprocess import Popen, DEVNULL
            Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"], stdout=DEVNULL, stderr=DEVNULL)
            os.environ["DISPLAY"] = ":99"
            time.sleep(1.0)
            print("✅ Xvfb started on :99 (best-effort).")
        except Exception:
            print("⚠️ Could not start Xvfb (perhaps not installed). Continuing without it.")

    # recommended browser args for CI/root environments
    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-popup-blocking",
        "--disable-blink-features=AutomationControlled",
        "--remote-debugging-pipe",
        f"--user-agent={BROWSER_USER_AGENT}",
    ]

    # try to detect a chrome binary (helpful in GH Actions)
    chrome_candidates = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]
    chrome_path = next((p for p in chrome_candidates if os.path.exists(p)), None)
    if chrome_path:
        print("🔎 Detected chromium binary:", chrome_path)
    else:
        print("🔎 Chromium binary not detected via standard paths; nodriver will try defaults.")

    try:
        print("🚀 Starting nodriver...")
        # start nodriver (pass args directly)
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

        # inject stealth init script if supported: try page.add_init_script
        # we'll try to add a script to hide webdriver and set userAgent in navigator
        try:
            page = await browser.get("about:blank")  # get a page object to call add_init_script
            # many nodriver/playwright-like pages support add_init_script
            init_script = f"""
                Object.defineProperty(navigator, 'webdriver', {{
                    get: () => undefined
                }});
                try {{
                    // override userAgent
                    Object.defineProperty(navigator, 'userAgent', {{
                        get: () => "{BROWSER_USER_AGENT}"
                    }});
                }} catch(e){{}}
            """
            add_init = getattr(page, "add_init_script", None)
            if callable(add_init):
                try:
                    await page.add_init_script(init_script)
                    print("💉 Injected init script via page.add_init_script()")
                except Exception:
                    # some nodriver versions might not support add_init_script on page
                    print("⚠️ add_init_script attempted but failed; continuing.")
            else:
                # if add_init_script not available, try evaluate before navigation later (best-effort)
                print("ℹ️ page.add_init_script not available; will attempt evaluate() after navigation.")
        except Exception:
            # if any of that failed we ignore and continue
            pass

        # now navigate to target url
        page = await browser.get(url)

        # If add_init_script wasn't available, attempt to run evaluate early to unset webdriver
        try:
            await page.evaluate("() => { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); }")
            # also try to override userAgent (best-effort)
            await page.evaluate(f"() => {{ try{{ Object.defineProperty(navigator, 'userAgent', {{get: () => '{BROWSER_USER_AGENT}'}}); }} catch(e){{}} }}")
        except Exception:
            # ignore errors here
            pass

        # initial title check (some pages put challenge text instantly)
        try:
            initial_title = await page.evaluate("document.title")
        except Exception:
            initial_title = None

        print("Initial title:", repr(initial_title))

        # wait until title changes from initial challenge text or just until it's not containing 'Just a moment'
        deadline = time.time() + max_wait
        last_title = initial_title
        while time.time() < deadline:
            try:
                cur_title = await page.evaluate("document.title")
            except Exception:
                cur_title = None

            # debug print occasionally
            if cur_title != last_title:
                print("Title changed:", repr(cur_title))
                last_title = cur_title

            # If title exists and doesn't contain the Cloudflare phrase, assume page passed
            if cur_title and "Just a moment" not in cur_title and "just a moment" not in cur_title.lower():
                final_title = cur_title
                print("✅ Challenge passed (title looks real):", final_title)
                # attempt graceful stop
                try:
                    browser.stop()
                except Exception:
                    try:
                        await getattr(browser, "close", lambda: None)()
                    except Exception:
                        pass
                return final_title

            await asyncio.sleep(POLL_INTERVAL)

        # timeout reached: grab whatever title we have now
        try:
            final_title = await page.evaluate("document.title")
        except Exception:
            final_title = last_title

        print("⚠️ Timeout waiting for challenge to pass. Last title:", repr(final_title))

        # cleanup
        try:
            browser.stop()
        except Exception:
            try:
                await getattr(browser, "close", lambda: None)()
            except Exception:
                pass

        return final_title

    except Exception as e:
        print("❌ nodriver attempt failed:", e)
        traceback.print_exc()
        return None


async def main():
    title = await get_title_nodriver_wait(URL, max_wait=MAX_WAIT_SECONDS)
    if title:
        print("🎯 Got title via nodriver:", title)
    else:
        print("ℹ️ nodriver failed or returned no usable title; trying requests fallback.")
        title = requests_fallback(URL)

    print("FINAL TITLE:", title)
    save_result(URL, title)


if __name__ == "__main__":
    # Run using nodriver's loop helper if available, otherwise asyncio.run
    if uc is not None and hasattr(uc, "loop"):
        try:
            uc.loop().run_until_complete(main())
        except Exception:
            asyncio.run(main())
    else:
        asyncio.run(main())
