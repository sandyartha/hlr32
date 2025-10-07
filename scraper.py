import asyncio
import nodriver
import re

async def get_title(url):
    # ✅ tambahkan no_sandbox=True agar bisa jalan di root
    browser = await nodriver.start(no_sandbox=True, headless=True)

    page = await browser.get(url)
    html = await page.get_content()

    # cari tag <title>
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
