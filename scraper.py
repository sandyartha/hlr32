import asyncio
import nodriver

async def get_title(url):
    browser = await nodriver.start()
    page = await browser.get(url)
    html = await page.get_content()
    # cari tag <title> dari html
    import re
    m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    title = m.group(1).strip() if m else None

    # tutup tab & browser
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
