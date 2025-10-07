import asyncio
import nodriver
import requests
from bs4 import BeautifulSoup

async def get_title_nodriver(url: str):
    try:
        print("🚀 Mencoba menggunakan nodriver...")

        # Jalankan browser dalam mode headless + no_sandbox
        browser = await nodriver.start(
            browser_args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--disable-extensions",
                "--remote-debugging-pipe",
                "--headless=new"
            ]
        )

        page = await browser.get(url)
        await page.wait(3)

        title = await page.title()
        print(f"✅ Berhasil ambil title: {title}")

        await browser.close()
        return title

    except Exception as e:
        print(f"❌ nodriver gagal: {e}")
        return None


def get_title_requests(url: str):
    try:
        print("🌐 Fallback: menggunakan requests (browser-like headers)...")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0.0.0 Safari/537.36"
            )
        }
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else None
        print(f"✅ Berhasil ambil title pakai requests: {title}")
        return title

    except Exception as e:
        print(f"❌ Gagal ambil title pakai requests: {e}")
        return None


async def main():
    url = "https://www.nowsecure.nl/"
    title = await get_title_nodriver(url)

    if not title:
        title = get_title_requests(url)

    print(f"🎯 Hasil akhir: {title}")


if __name__ == "__main__":
    asyncio.run(main())
