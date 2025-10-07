import asyncio
import nodriver
import re
import os

async def get_title(url):
    # Gunakan path Chrome eksplisit jika environment tidak otomatis
    chrome_path = os.getenv("CHROME_PATH", "/usr/bin/chromium-browser")

    browser = await nodriver.start(
        no_sandbox=True,
        headless=True,
        browser_executable_path=chrome_path
    )

    page = await browser.get(url)
    html = await page.get_content()

    m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = m.group(1).strip() if m else None

    await page.close()
    browser.stop()
    await asyncio.sleep(1)
    return title

async def main():
    url = 'https://www.nowsecure.nl'
    title = await get_title(url)
    print("Title halaman:", title)

if __name__ == '__main__':
    asyncio.run(main())
