import time
from typing import List, Dict

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import win32gui
import win32con


async def get_parsed_content(
        username: str,
        user_id: int,
        story_content_type_id: int,
        post_content_type_id: int,
        photo_media_type_id: int,
        video_media_type_id: int
) -> List[Dict]:
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    parsed_content = []

    try:
        # Налаштовуємо headless режим
        driver.get(f"https://iqsaved.com/viewer/{username}/")
        # time.sleep(1)
        # hide_chrome_window()

        wait = WebDriverWait(driver, 60)

        # Чекаємо на появу елементів з контентом постів
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.profile-tabs__content-item.profile-tabs__posts ul.media-items")
        ))

        # Чекаємо на пости
        posts_links = driver.find_elements(By.CSS_SELECTOR,
                                           "div.profile-tabs__content-item.profile-tabs__posts "
                                           "ul.media-items "
                                           "li.media-items__item "
                                           "div.media-items__info "
                                           "div.media-items__action "
                                           "a[download]"
                                           )

        print(f"Пости {username}:")
        for i, link in enumerate(posts_links, 1):
            url = link.get_attribute("href")
            file_name = link.get_attribute("download")
            media_type = await get_media_type(url)
            media_type_id = await get_media_type_id(media_type, video_media_type_id, photo_media_type_id)

            content_item = await get_content_item(
                "Post",
                media_type,
                media_type_id,
                post_content_type_id,
                user_id,
                username,
                file_name,
                url
            )
            parsed_content.append(content_item)

            print(f"{i}. URL: {url}\n   Назва: {file_name}")

        # Чекаємо на Сторіс (опційно, якщо вони є)
        stories_links = driver.find_elements(By.CSS_SELECTOR,
                                             "div.profile-tabs__content-item.profile-tabs__stories "
                                             "ul.media-items "
                                             "li.media-items__item "
                                             "div.media-items__info "
                                             "div.media-items__action "
                                             "a[download]"
                                             )

        print(f"Сторіс {username}:")
        for i, link in enumerate(stories_links, 1):
            url = link.get_attribute("href")
            file_name = link.get_attribute("download")
            media_type = await get_media_type(url)
            media_type_id = await get_media_type_id(media_type, video_media_type_id, photo_media_type_id)

            content_item = await get_content_item(
                "Story",
                media_type,
                media_type_id,
                story_content_type_id,
                user_id,
                username,
                file_name,
                url
            )
            parsed_content.append(content_item)

            print(f"{i}. URL: {url}\n   Назва: {file_name}")

    finally:
        driver.quit()

    return parsed_content


async def get_content_item(content_type, media_type, media_type_id, content_type_id, user_id, username, file_name, url):
    content_item = {
        'content_type': content_type,
        'content_type_id': content_type_id,
        'media_type': media_type,
        'media_type_id': media_type_id,
        'username': username,
        'user_id': user_id,
        'file_name': file_name,
        'url': url
    }
    return content_item


async def get_media_type(url):
    if url.endswith(".mp4"):
        return "Video"
    else:
        return "Photo"


async def get_media_type_id(media_type, video_media_type_id, photo_media_type_id):
    if media_type == "Video":
        return video_media_type_id
    else:
        return photo_media_type_id


def hide_chrome_window():
    def callback(hwnd, _):
        title = win32gui.GetWindowText(hwnd)
        if "Chrome" in title:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)  # або SW_MINIMIZE
    win32gui.EnumWindows(callback, None)
