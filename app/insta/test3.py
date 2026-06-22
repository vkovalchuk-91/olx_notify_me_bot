import asyncio
import re
from urllib.parse import unquote, urlparse, parse_qs
from playwright.async_api import async_playwright


def extract_filename_from_url(instabooster_url: str) -> str:
    # Отримати значення параметра 'url='
    parsed = urlparse(instabooster_url)
    query = parsed.query
    file_url_match = re.search(r'url=(https[^&]+)', query)
    if not file_url_match:
        return ""

    encoded_file_url = file_url_match.group(1)
    decoded_url = unquote(encoded_file_url)

    # Виділяємо ім'я файлу з decoded URL
    filename_match = re.search(r'/([^/?#]+\.((mp4)|(jpg)|(png)))', decoded_url)
    if filename_match:
        return filename_match.group(1)
    return ""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Можна зробити headless=True
        context = await browser.new_context()
        page = await context.new_page()

        # 1. Перейти на сайт
        await page.goto("https://instabooster.com.ua/divitis-storis-z-instagram-anonimno/")

        # 2. Ввести ім'я користувача
        await page.fill("input#url", "tati_0904_")

        # 3. Натиснути кнопку "Дивитися"
        await page.click("button.button")

        # 4. Дочекатися появи елементів із класом download-stories-preview--item
        await page.wait_for_selector("li.download-stories-preview--item", timeout=15000)

        # 5. Знайти всі елементи <li class="download-stories-preview--item">
        story_items = await page.query_selector_all("li.download-stories-preview--item")

        print(f"Знайдено {len(story_items)} історій:")

        # 6. Вивести значення <a href= з кожного блоку
        for idx, item in enumerate(story_items, 1):
            a_tag = await item.query_selector("a")
            if a_tag:
                href = await a_tag.get_attribute("href")
                full_url = f"https://instabooster.com.ua{href}"
                filename = extract_filename_from_url(full_url)
                print(f"{idx}. {filename}\n {full_url}")

        await browser.close()

asyncio.run(main())
