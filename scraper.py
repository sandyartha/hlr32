import nodriver as uc
from bs4 import BeautifulSoup
import requests
import asyncio

URL = "https://www.nowsecure.nl"

async def get_title_nodriver(url: str):
    print("🚀 Mencoba menggunakan nodriver...")

    try:
        browser = await uc.start(
            no_sandbox=True,
            headless=True,
            browser_args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                "--remote-debugging-pipe",
            ]
        )
        page = await browser.get(url)
        await page.wait_for("title")
        title = await page.evaluate("document.title")
        await browser.stop()
        return title

    except Exception as e:
        print(f"❌ nodriver gagal:\n{e}\n")
        return None


def get_title_requests(url: str):
    print("🌐 Fallback: menggunakan requests (browser-like headers)...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.text.strip() if soup.title else None
        print(f"✅ Berhasil ambil title pakai requests: {title}")
        return title
    except Exception as e:
        print(f"❌ Gagal ambil title pakai requests: {e}")
        return None


async def main():
    title = await get_title_nodriver(URL)

    if not title:
        title = get_title_requests(URL)

    print(f"🎯 Hasil akhir: {title}")


if __name__ == "__main__":
    uc.loop().run_until_complete(main())
