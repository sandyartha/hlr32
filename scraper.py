#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scraper.py
Script universal untuk ambil <title> dari halaman web
- Prioritas: nodriver (stealth browser)
- Fallback: requests (browser-like headers)
Aman digunakan di server/headless/root environments.
"""

import asyncio
import nodriver as uc
import requests
from bs4 import BeautifulSoup

# ==========================================
# Fungsi ambil title pakai nodriver
# ==========================================
async def get_title_nodriver(url: str):
    print("🚀 Mencoba menggunakan nodriver...")
    config = uc.Config()
    config.headless = True
    config.no_sandbox = True
    config.browser_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-gpu",
    ]
    config.lang = "en-US"

    try:
        browser = await uc.start(config)
        page = await browser.get(url)
        await page.wait_loaded()

        title = await page.evaluate("document.title")
        print(f"🎯 Title ditemukan: {title}")

        await browser.stop()
        return title

    except Exception as e:
        print(f"❌ nodriver gagal:\n{e}")
        return None


# ==========================================
# Fallback: ambil title via requests + BeautifulSoup
# ==========================================
def get_title_requests(url: str):
    print("🌐 Fallback: menggunakan requests (browser-like headers)...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title else None
        print(f"🎯 Title ditemukan via requests: {title}")
        return title
    except Exception as e:
        print(f"❌ Gagal ambil title pakai requests: {e}")
        return None


# ==========================================
# Main logic
# ==========================================
async def main():
    url = "https://www.nowsecure.nl"

    # 1️⃣ Coba pakai nodriver
    title = await get_title_nodriver(url)

    # 2️⃣ Fallback jika gagal
    if not title:
        title = get_title_requests(url)

    print(f"🏁 Hasil akhir: {title}")


# ==========================================
# Entry point (tanpa asyncio.run untuk nodriver)
# ==========================================
if __name__ == "__main__":
    uc.loop().run_until_complete(main())
