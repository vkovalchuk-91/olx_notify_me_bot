import asyncio
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
import time


def extract_filename_from_url(url: str) -> str:
    # Розбираємо URL і отримуємо параметри запиту
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Шукаємо параметр "filename" у запиті
    filename = query_params.get('filename', [None])[0]

    # Перевірка, чи знайшовся файл, і повернення результату
    if filename:
        return filename
    else:
        return "Назву файлу не вдалося знайти."


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=True для фонової роботи
        page = await browser.new_page()

        # 1. Зайти на сайт
        await page.goto("https://anonyig.com/en/")

        # 2. Ввести username
        await page.fill('input[placeholder="@username or link"]', "tati_0904_")

        # 3. Натиснути на кнопку пошуку (зображення)
        await page.click('img[src="/img/search-icon.png?id=4534cc5327ea6eb828dbaa1e31ec85dc"]')

        # 4. Дочекатися появи першого елемента
        await page.wait_for_selector("li.profile-media-list__item", timeout=15000)

        # Час початку прокручування
        start_time = time.time()
        media_items_count = 0

        while media_items_count < 30 and time.time() - start_time < 10:
            # 5. Отримати кількість елементів на сторінці
            media_items = await page.query_selector_all("ul.profile-media-list li.profile-media-list__item")
            media_items_count = len(media_items)

            if media_items_count < 30:
                # Прокручувати сторінку вниз
                await page.evaluate("window.scrollBy(0, window.innerHeight * 2);")
                await page.wait_for_timeout(3000)  # Чекати 3 секунди між прокручуваннями

        print(f"Знайдено {media_items_count} медіа-елементів.")

        # 6. З кожного витягнути посилання на завантаження
        for index, item in enumerate(media_items, start=1):
            download_btn = await item.query_selector('a.button.button--filled.button__download')
            if download_btn:
                href = await download_btn.get_attribute("href")
                filename = extract_filename_from_url(href)
                print(f"{index}. {filename}\n {href}")

        # 6. Знайти кнопку "stories" і натиснути
        await page.click('button.tabs-component__button:has-text("stories")')

        # 7. Дочекатися появи медіа-елементів
        await page.wait_for_selector("li.profile-media-list__item", timeout=15000)

        # Час початку прокручування
        start_time = time.time()
        media_items_count = 0
        previous_media_items_count = -1

        while previous_media_items_count != media_items_count:
            previous_media_items_count = media_items_count
            # 5. Отримати кількість елементів на сторінці
            media_items = await page.query_selector_all("ul.profile-media-list li.profile-media-list__item")
            media_items_count = len(media_items)
            # Прокручувати сторінку вниз
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2);")
            await page.wait_for_timeout(3000)  # Чекати 3 секунди між прокручуваннями

        print(f"Загалом знайдено {media_items_count} медіа-елементів у Stories.")

        # 6. З кожного витягнути посилання на завантаження
        for index, item in enumerate(media_items, start=1):
            download_btn = await item.query_selector('a.button.button--filled.button__download')
            if download_btn:
                href = await download_btn.get_attribute("href")
                filename = extract_filename_from_url(href)
                print(f"{index}. {filename}\n {href}")

        await browser.close()

asyncio.run(run())
