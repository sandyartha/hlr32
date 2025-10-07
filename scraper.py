import asyncio
import nodriver
import os
import subprocess
import requests
from bs4 import BeautifulSoup

# Deteksi jika environment tidak punya display (misal GitHub Actions)
def ensure_xvfb():
    if os.environ.get("DISPLAY") is None:
        print("🧩 Tidak ada DISPLAY, memulai Xvfb...")
        subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1024x768x24"])
        os.environ["DISPLAY"] = ":99"
        print("✅ Xvfb aktif pada DISPLAY=:99")

async def get_title_with_nodriver(url: str):
    try:
        print("🚀 Mencoba menggunakan nodriver...")

        # pastikan Xvfb aktif bila perlu
        ensure_xvfb()

        browser = await nodriver.start(
            no_sandbox=True,
            headless=True,
            disable_gpu=True,
            disable_dev_shm_usage=True,
            hide_scrollbars=True,
            disable_infobars=True,
        )

        page = await browser.get(url)
        await page.wait_for_load_state("load")

        title = await page.evaluate("document.title")
        await browser.close()
        return title
    except Exception as e:
        print(f"❌ nodriver gagal: {e}")
        return None

def get_title_with_requests(url: str):
    print("🌐 Fallback: menggunakan requests (browser-like headers)...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://google.com",
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        title_tag = soup.find("title")
        return title_tag.text.strip() if title_tag else None
    except Exception as e:
        print(f"❌ Gagal ambil title pakai requests: {e}")
        return None

async def main():
    url = "https://www.nowsecure.nl/"
    title = await get_title_with_nodriver(url)

    if not title:
        title = get_title_with_requests(url)

    print(f"🎯 Hasil akhir: {title}")

if __name__ == "__main__":
    asyncio.run(main())
