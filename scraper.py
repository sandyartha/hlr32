import asyncio
import nodriver
import traceback
import requests
from bs4 import BeautifulSoup

URL = "https://www.nowsecure.nl"

async def get_title_with_nodriver(url: str) -> str:
    """Coba ambil title menggunakan nodriver (browser)."""
    print("🚀 Mencoba menggunakan nodriver...")

    try:
        browser = await nodriver.start(
            browser_executable_path="/usr/bin/chromium-browser",  # ubah sesuai sistem
            no_sandbox=True,
            headless=True,
            browser_args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-zygote",
                "--single-process",
                "--remote-debugging-port=0",
            ],
        )

        page = await browser.get(url)
        title_elem = await page.select("title")

        if title_elem:
            title_text = await title_elem.text()
        else:
            title_text = "Tidak ditemukan <title>"

        await browser.stop()
        print("✅ Dapat title dari nodriver:", title_text)
        return title_text

    except Exception as e:
        print("❌ nodriver gagal:", e)
        traceback.print_exc()
        return None


def get_title_with_requests(url: str) -> str:
    """Fallback ke requests jika browser gagal."""
    print("🌐 Fallback: menggunakan requests...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("title")
        title_text = title_tag.text.strip() if title_tag else "Tidak ditemukan <title>"
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
