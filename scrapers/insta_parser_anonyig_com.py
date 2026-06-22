import asyncio
import logging
import os
import time
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, async_playwright

logger = logging.getLogger(__name__)


async def get_parsed_content(username: str, user_id: int) -> List[Dict]:
    parsed_content: List[Dict] = []
    logger.info('Instagram scraper: opening anonyig.com for @%s', username)

    async with async_playwright() as playwright:
        browser = await _launch_browser(playwright)
        try:
            context = await browser.new_context(
                ignore_https_errors=True,
                viewport={'width': 1365, 'height': 1600},
            )
            page = await context.new_page()
            page.set_default_timeout(60_000)
            await page.goto('https://anonyig.com/en/', wait_until='domcontentloaded')
            await _search_username(page, username)

            try:
                await page.wait_for_selector('li.profile-media-list__item', timeout=5_000)
                media_items = await _collect_media_items(page, max_items=30, max_seconds=10, pause_seconds=2)
                parsed_content.extend(await _extract_items(media_items, 'Post', user_id, username))
            except PlaywrightTimeoutError:
                logger.info('Instagram scraper: @%s posts tab did not load within 5 sec', username)

            if await _switch_to_stories_tab(page):
                try:
                    await page.wait_for_selector('li.profile-media-list__item', timeout=5_000)
                    media_items = await _collect_media_items(page, stop_when_stable=True, pause_seconds=3)
                    parsed_content.extend(await _extract_items(media_items, 'Story', user_id, username))
                except PlaywrightTimeoutError:
                    logger.info('Instagram scraper: @%s stories tab did not load within 5 sec', username)
        finally:
            await browser.close()

    logger.info('Instagram scraper: finished @%s, total downloadable items=%s', username, len(parsed_content))
    return parsed_content


async def _launch_browser(playwright):
    args = [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--ignore-certificate-errors',
    ]
    chrome_bin = os.getenv('CHROME_BIN', '').strip()
    if chrome_bin:
        logger.info('Instagram scraper: using Chrome at %s', chrome_bin)
        return await playwright.chromium.launch(headless=True, executable_path=chrome_bin, args=args)
    logger.info('Instagram scraper: using Playwright bundled Chromium')
    return await playwright.chromium.launch(headless=True, args=args)


async def _search_username(page: Page, username: str) -> None:
    await page.wait_for_selector('body')
    search_input = await _find_search_input(page)
    if not search_input:
        raise PlaywrightTimeoutError('Anonyig search input not found')
    await search_input.fill(username)
    if not await _click_search_button(page):
        await search_input.press('Enter')


async def _find_search_input(page: Page) -> Optional[Locator]:
    selectors = [
        'input[placeholder="@username or link"]',
        'input[placeholder*="username"]',
        'input[type="search"]',
        'input[type="text"]',
        'form input',
    ]
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(await locator.count()):
            element = locator.nth(index)
            if await element.is_visible() and await element.is_enabled():
                return element
    return None


async def _click_search_button(page: Page) -> bool:
    for selector in ('img[src*="search"]', 'button[type="submit"]', 'form button'):
        locator = page.locator(selector)
        for index in range(await locator.count()):
            element = locator.nth(index)
            if not await element.is_visible():
                continue
            try:
                await element.click(timeout=2_000)
                return True
            except PlaywrightTimeoutError:
                await element.evaluate('element => element.click()')
                return True
    return False


async def _collect_media_items(
    page: Page,
    max_items: Optional[int] = None,
    max_seconds: int = 20,
    pause_seconds: int = 2,
    stop_when_stable: bool = False,
) -> Locator:
    start_time = time.time()
    previous_count = -1
    locator = page.locator('ul.profile-media-list li.profile-media-list__item')
    while time.time() - start_time < max_seconds:
        count = await locator.count()
        if max_items and count >= max_items:
            break
        if stop_when_stable and previous_count == count:
            break
        previous_count = count
        await page.evaluate('window.scrollBy(0, window.innerHeight * 2)')
        await asyncio.sleep(pause_seconds)
    return locator


async def _switch_to_stories_tab(page: Page) -> bool:
    stories_tab = page.locator('li.tabs-component__item').filter(
        has=page.locator('button.tabs-component__button', has_text='stories')
    ).first
    if await stories_tab.count() == 0:
        return False
    button = stories_tab.locator('button.tabs-component__button').first
    button_class = await button.get_attribute('class') or ''
    if 'tabs-component__button--disabled' in button_class:
        return False
    try:
        await stories_tab.click(timeout=2_000)
        return True
    except PlaywrightTimeoutError:
        return False


async def _extract_items(media_items: Locator, content_type: str, user_id: int, username: str) -> List[Dict]:
    items: List[Dict] = []
    for index in range(await media_items.count()):
        item = media_items.nth(index)
        download_btn = item.locator('a.button.button--filled.button__download').first
        if await download_btn.count() == 0:
            continue
        url = await download_btn.get_attribute('href')
        if not url:
            continue
        items.append({
            'content_type': content_type,
            'media_type': 'Video' if '.mp4' in url else 'Photo',
            'username': username,
            'user_id': user_id,
            'file_name': extract_filename_from_url(url),
            'url': url,
        })
    return items


def extract_filename_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    filename = parse_qs(parsed_url.query).get('filename', [None])[0]
    return filename or 'unknown_filename'
