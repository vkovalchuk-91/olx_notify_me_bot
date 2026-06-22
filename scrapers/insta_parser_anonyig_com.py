import logging
import time
from typing import Dict, List
from urllib.parse import parse_qs, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def get_parsed_content(username: str, user_id: int) -> List[Dict]:
    parsed_content = []
    logger.info('Instagram scraper: opening anonyig.com for @%s', username, extra={'job_name': 'check_insta'})
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.goto('https://anonyig.com/en/')
            await page.fill('input[placeholder="@username or link"]', username)
            await page.click('img[src="/img/search-icon.png?id=4534cc5327ea6eb828dbaa1e31ec85dc"]')

            try:
                await page.wait_for_selector('li.profile-media-list__item', timeout=5000)
                start_time = time.time()
                media_items_count = 0
                media_items = []
                while media_items_count < 30 and time.time() - start_time < 10:
                    media_items = await page.query_selector_all('ul.profile-media-list li.profile-media-list__item')
                    media_items_count = len(media_items)
                    if media_items_count < 30:
                        await page.evaluate('window.scrollBy(0, window.innerHeight * 2);')
                        await page.wait_for_timeout(2000)
                post_items = await _extract_items(media_items, 'Post', user_id, username)
                logger.info(
                    'Instagram scraper: @%s posts tab found %s media cards, %s downloadable items',
                    username,
                    media_items_count,
                    len(post_items),
                    extra={'job_name': 'check_insta'},
                )
                parsed_content.extend(post_items)
            except PlaywrightTimeoutError:
                logger.info(
                    'Instagram scraper: @%s posts tab did not load within 5 sec',
                    username,
                    extra={'job_name': 'check_insta'},
                )

            if await _switch_to_stories_tab(page, username):
                try:
                    await page.wait_for_selector('li.profile-media-list__item', timeout=5000)
                    media_items_count = 0
                    previous_count = -1
                    media_items = []
                    while previous_count != media_items_count:
                        previous_count = media_items_count
                        media_items = await page.query_selector_all('ul.profile-media-list li.profile-media-list__item')
                        media_items_count = len(media_items)
                        await page.evaluate('window.scrollBy(0, window.innerHeight * 2);')
                        await page.wait_for_timeout(3000)
                    story_items = await _extract_items(media_items, 'Story', user_id, username)
                    logger.info(
                        'Instagram scraper: @%s stories tab found %s media cards, %s downloadable items',
                        username,
                        media_items_count,
                        len(story_items),
                        extra={'job_name': 'check_insta'},
                    )
                    parsed_content.extend(story_items)
                except PlaywrightTimeoutError:
                    logger.info(
                        'Instagram scraper: @%s stories tab did not load within 5 sec',
                        username,
                        extra={'job_name': 'check_insta'},
                    )

        finally:
            await browser.close()
    logger.info(
        'Instagram scraper: finished @%s, total downloadable items=%s',
        username,
        len(parsed_content),
        extra={'job_name': 'check_insta'},
    )
    return parsed_content


async def _switch_to_stories_tab(page, username: str) -> bool:
    stories_tab = page.locator(
        'li.tabs-component__item:has(button.tabs-component__button:has-text("stories"))'
    )
    stories_button = stories_tab.locator('button.tabs-component__button')

    if await stories_button.count() == 0:
        logger.info(
            'Instagram scraper: @%s has no stories tab on page',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False

    button_class = await stories_button.get_attribute('class') or ''
    if 'tabs-component__button--disabled' in button_class:
        logger.info(
            'Instagram scraper: @%s stories tab is disabled, probably no active stories',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False

    try:
        await stories_tab.click(timeout=5000)
        logger.info('Instagram scraper: opened @%s stories tab', username, extra={'job_name': 'check_insta'})
        return True
    except PlaywrightTimeoutError:
        logger.info(
            'Instagram scraper: could not open @%s stories tab within 5 sec',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False


async def _extract_items(media_items, content_type: str, user_id: int, username: str) -> List[Dict]:
    items = []
    for item in media_items:
        download_btn = await item.query_selector('a.button.button--filled.button__download')
        if not download_btn:
            continue
        url = await download_btn.get_attribute('href')
        file_name = extract_filename_from_url(url)
        media_type = 'Video' if url.endswith('.mp4') else 'Photo'
        items.append({
            'content_type': content_type,
            'media_type': media_type,
            'username': username,
            'user_id': user_id,
            'file_name': file_name,
            'url': url,
        })
    return items


def extract_filename_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    filename = query_params.get('filename', [None])[0]
    return filename or 'unknown_filename'
