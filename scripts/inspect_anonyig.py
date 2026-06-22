import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

URLS = [
    'https://anonyig.com/en/',
    'https://anonyig.com/en/instagram/testuser',
    'https://anonyig.com/en/profile/testuser',
    'https://anonyig.com/en/viewer/testuser',
]


async def inspect_page(page, url: str) -> None:
    print('---', url)
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    print('url', page.url)
    print('title', await page.title())
    inputs = await page.eval_on_selector_all(
        'input, textarea',
        'els => els.map(el => ({placeholder: el.placeholder, name: el.name, type: el.type, id: el.id, className: el.className}))',
    )
    print('inputs', inputs)
    buttons = await page.eval_on_selector_all(
        'button, img[src*="search"], [type="submit"], form',
        'els => els.map(el => ({tag: el.tagName, text: (el.innerText || "").slice(0,80), src: el.getAttribute("src"), className: el.className, action: el.getAttribute("action")}))',
    )
    print('buttons/forms', buttons[:20])
    media = await page.query_selector_all('li.profile-media-list__item')
    print('media_items', len(media))
    html = await page.content()
    Path('/tmp/anonyig.html').write_text(html[:50000], encoding='utf-8')
    print('html_saved', min(len(html), 50000))


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        for url in URLS:
            try:
                await inspect_page(page, url)
            except Exception as exc:
                print('error', exc)
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
