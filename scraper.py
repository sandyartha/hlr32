import asyncio
import os
import re
import sys

try:
    import nodriver
except Exception as e:
    sys.exit(f"Failed to import nodriver: {e}\nInstall with: python -m pip install git+https://github.com/ultrafunkamsterdam/nodriver.git")


async def get_title(url: str) -> str | None:
    """Start a browser, open url, return the page <title> (or None).

    This function uses the nodriver API and attempts to stop the browser
    cleanly whether stop() is a coroutine or regular function.
    """
    async def _start_browser_with_fallback():
        """Try to start nodriver normally; on failure retry with no-sandbox flags.

        This helps running under CI where Chrome may require --no-sandbox.
        """
        try:
            return await nodriver.start()
        except Exception as e:
            print("nodriver.start() failed, retrying with adjusted flags:", e)
            # build fallback options
            opts: dict = {}
            chrome_bin = os.environ.get('CHROME_BIN')
            if chrome_bin:
                opts['executable_path'] = chrome_bin

            # Respect environment variables to control sandboxing and headless mode
            no_sandbox = os.environ.get('NO_SANDBOX') in ('1', 'true', 'True')
            headless_env = os.environ.get('HEADLESS') in ('1', 'true', 'True')

            args = []
            if no_sandbox:
                args += ['--no-sandbox', '--disable-setuid-sandbox']
            # common flag to avoid /dev/shm issues in containers
            args += ['--disable-dev-shm-usage']

            if args:
                opts['args'] = args

            if headless_env:
                opts['headless'] = True

            try:
                return await nodriver.start(**opts)
            except Exception as e2:
                print('Retry with adjusted flags also failed:', e2)
                raise

    browser = await _start_browser_with_fallback()
    page = await browser.get(url)

    html = None
    try:
        html = await page.get_content()
    except Exception:
        # fall back to trying to get title via page API if available
        pass

    title = None
    if html:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

    # tutup tab & browser (handle both coroutine and regular function)
    try:
        await page.close()
    except Exception:
        try:
            res = page.close()
            if asyncio.iscoroutine(res):
                await res
        except Exception:
            pass

    try:
        res = browser.stop()
        if asyncio.iscoroutine(res):
            await res
    except Exception:
        # swallow stop errors on cleanup
        pass

    # small pause to let cleanup complete
    await asyncio.sleep(0.5)

    return title


async def main():
    url = os.environ.get('SCRAPE_URL', 'https://www.nowsecure.nl')
    title = await get_title(url)
    print("Title halaman:", title or '<no title found>')


if __name__ == '__main__':
    asyncio.run(main())
