import asyncio
import nodriver
import re
import os

async def get_title(url):
    # Coba beberapa path umum di GitHub Actions
    chrome_candidates = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/snap/bin/chromium"
    ]
    chrome_path = next((p for p in chrome_candidates if os.path.exists(p)), None)

    if not chrome_path:
        raise RuntimeError("Chromium tidak ditemukan di sistem!")

    print(f"✅ Menggunakan browser: {chrome_path}")

    browser = await nodriver.start(
        browser_executable_path=chrome_path,
        no_sandbox=True,
        headless=True,
    )

    page = await browser.get(url)
    html = await page.get_content()

    # Ambil <title>
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = m.group(1).strip() if m else "Title tidak ditemukan"

    await page.close()
    browser.stop()
    await asyncio.sleep(1)
    return title

async def main():
    url = "https://www.nowsecure.nl"
    title = await get_title(url)
    print("🎯 Title halaman:", title)

if __name__ == "__main__":
    asyncio.run(main())
