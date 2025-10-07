import asyncio
import nodriver
import traceback
import os
import requests
from bs4 import BeautifulSoup


URL = "https://www.nowsecure.nl"


async def get_title_with_nodriver(url: str) -> str:
    """Ambil title menggunakan nodriver, dengan konfigurasi fix untuk root/headless."""
    print("🚀 Mencoba menggunakan nodriver...")

    try:
        browser = await nodriver.start(
            no_sandbox=True,
            headless=True,
            browser_path="/usr/bin/chromium-browser",
            browser_args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-zygote",
                "--single-process",
                "--disable-software-rasterizer",
                "--remote-debugging-port=0",
            ],
        )

        page = await browser.get(url)
        title_elem = await page.select("title")

        title_text = await title_elem.text() if title_elem else "❌ Tidak ditemukan <title>"
        await page.close()
        await browser.stop()
        print("✅ Dapat title dari nodriver:", title_text)
        return title_text

    except Exception as e:
        print("❌ nodriver gagal:", e)
        traceback.print_exc()
        return None


def get_title_with_requests(url: str) -> str:
    """Fallback dengan headers mirip browser."""
    print("🌐 Fallback: menggunakan requests (browser-like headers)...")
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://google.com",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("title")
        title_text = title_tag.text.strip() if title_tag else "❌ Tidak ditemukan <title>"
        print("✅ Dapat title dari requests:", title_text)
        return title_text

    except Exception as e:
        print("❌ Gagal ambil title pakai requests:", e)
        return None


async def main():
    url = URL
    title = await get_title_with_nodriver(url)
    if not title:
        title = get_title_with_requests(url)
    print("\n🎯 Hasil akhir:", title)


if __name__ == "__main__":
    asyncio.run(main())
