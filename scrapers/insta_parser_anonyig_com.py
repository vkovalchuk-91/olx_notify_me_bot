import asyncio
import logging
import os
import shutil
import time
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


async def get_parsed_content(username: str, user_id: int) -> List[Dict]:
    return await asyncio.to_thread(_get_parsed_content_sync, username, user_id)


def _get_parsed_content_sync(username: str, user_id: int) -> List[Dict]:
    parsed_content = []
    logger.info('Instagram scraper: opening anonyig.com for @%s', username, extra={'job_name': 'check_insta'})
    driver = _create_driver()
    try:
        driver.get('https://anonyig.com/en/')
        _search_username(driver, username)

        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'li.profile-media-list__item'))
            )
            media_items = _collect_media_items(driver, max_items=30, max_seconds=10, pause_seconds=2)
            post_items = _extract_items(media_items, 'Post', user_id, username)
            logger.info(
                'Instagram scraper: @%s posts tab found %s media cards, %s downloadable items',
                username,
                len(media_items),
                len(post_items),
                extra={'job_name': 'check_insta'},
            )
            parsed_content.extend(post_items)
        except TimeoutException:
            logger.info(
                'Instagram scraper: @%s posts tab did not load within 5 sec',
                username,
                extra={'job_name': 'check_insta'},
            )

        if _switch_to_stories_tab(driver, username):
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.profile-media-list__item'))
                )
                media_items = _collect_media_items(driver, stop_when_stable=True, pause_seconds=3)
                story_items = _extract_items(media_items, 'Story', user_id, username)
                logger.info(
                    'Instagram scraper: @%s stories tab found %s media cards, %s downloadable items',
                    username,
                    len(media_items),
                    len(story_items),
                    extra={'job_name': 'check_insta'},
                )
                parsed_content.extend(story_items)
            except TimeoutException:
                logger.info(
                    'Instagram scraper: @%s stories tab did not load within 5 sec',
                    username,
                    extra={'job_name': 'check_insta'},
                )
    finally:
        driver.quit()

    logger.info(
        'Instagram scraper: finished @%s, total downloadable items=%s',
        username,
        len(parsed_content),
        extra={'job_name': 'check_insta'},
    )
    return parsed_content


def _create_driver() -> WebDriver:
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--window-size=1365,1600')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    )

    chrome_binary = os.getenv('CHROME_BIN') or shutil.which('chromium') or shutil.which('chromium-browser')
    if chrome_binary:
        options.binary_location = chrome_binary

    chromedriver = shutil.which('chromedriver')
    service = Service(chromedriver) if chromedriver else None
    driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def _search_username(driver: WebDriver, username: str) -> None:
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    search_input = _find_search_input(driver)
    if not search_input:
        logger.warning(
            'Instagram scraper: anonyig search input not found for @%s; url=%s title=%s',
            username,
            driver.current_url,
            driver.title,
            extra={'job_name': 'check_insta'},
        )
        raise TimeoutException('Anonyig search input not found')

    search_input.clear()
    search_input.send_keys(username)

    if not _click_search_button(driver):
        search_input.send_keys(Keys.ENTER)


def _find_search_input(driver: WebDriver) -> Optional[WebElement]:
    selectors = [
        'input[placeholder="@username or link"]',
        'input[placeholder*="username"]',
        'input[placeholder*="Username"]',
        'input[type="search"]',
        'input[type="text"]',
        'form input',
    ]
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                return element
    return None


def _click_search_button(driver: WebDriver) -> bool:
    selectors = [
        'img[src*="search"]',
        'button[type="submit"]',
        'form button',
        '[role="button"]',
    ]
    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            if not element.is_displayed():
                continue
            try:
                element.click()
                return True
            except WebDriverException:
                driver.execute_script('arguments[0].click();', element)
                return True
    return False


def _collect_media_items(
    driver: WebDriver,
    max_items: Optional[int] = None,
    max_seconds: int = 20,
    pause_seconds: int = 2,
    stop_when_stable: bool = False,
) -> List[WebElement]:
    start_time = time.time()
    previous_count = -1
    media_items: List[WebElement] = []

    while time.time() - start_time < max_seconds:
        media_items = driver.find_elements(By.CSS_SELECTOR, 'ul.profile-media-list li.profile-media-list__item')
        media_items_count = len(media_items)
        if max_items and media_items_count >= max_items:
            break
        if stop_when_stable and previous_count == media_items_count:
            break
        previous_count = media_items_count
        driver.execute_script('window.scrollBy(0, window.innerHeight * 2);')
        time.sleep(pause_seconds)

    return media_items


def _switch_to_stories_tab(driver: WebDriver, username: str) -> bool:
    stories_buttons = driver.find_elements(
        By.XPATH,
        '//li[contains(@class, "tabs-component__item")]'
        '[.//button[contains(@class, "tabs-component__button") and '
        'contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "stories")]]',
    )

    if not stories_buttons:
        logger.info(
            'Instagram scraper: @%s has no stories tab on page',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False

    stories_tab = stories_buttons[0]
    button = stories_tab.find_element(By.CSS_SELECTOR, 'button.tabs-component__button')
    button_class = button.get_attribute('class') or ''
    if 'tabs-component__button--disabled' in button_class:
        logger.info(
            'Instagram scraper: @%s stories tab is disabled, probably no active stories',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False

    try:
        stories_tab.click()
        logger.info('Instagram scraper: opened @%s stories tab', username, extra={'job_name': 'check_insta'})
        return True
    except WebDriverException:
        logger.info(
            'Instagram scraper: could not open @%s stories tab within 5 sec',
            username,
            extra={'job_name': 'check_insta'},
        )
        return False


def _extract_items(media_items: List[WebElement], content_type: str, user_id: int, username: str) -> List[Dict]:
    items = []
    for item in media_items:
        download_btns = item.find_elements(By.CSS_SELECTOR, 'a.button.button--filled.button__download')
        if not download_btns:
            continue
        url = download_btns[0].get_attribute('href')
        if not url:
            continue
        file_name = extract_filename_from_url(url)
        media_type = 'Video' if _is_video_url(url) else 'Photo'
        items.append({
            'content_type': content_type,
            'media_type': media_type,
            'username': username,
            'user_id': user_id,
            'file_name': file_name,
            'url': url,
        })
    return items


def _is_video_url(url: str) -> bool:
    parsed_url = urlparse(url)
    filename = parse_qs(parsed_url.query).get('filename', [''])[0]
    return parsed_url.path.endswith('.mp4') or filename.endswith('.mp4') or '.mp4' in url


def extract_filename_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    filename = query_params.get('filename', [None])[0]
    return filename or 'unknown_filename'
