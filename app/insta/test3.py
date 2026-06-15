import re
from urllib.parse import unquote, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def extract_filename_from_url(instabooster_url: str) -> str:
    parsed = urlparse(instabooster_url)
    file_url_match = re.search(r'url=(https[^&]+)', parsed.query)
    if not file_url_match:
        return ''

    decoded_url = unquote(file_url_match.group(1))
    filename_match = re.search(r'/([^/?#]+\.(mp4|jpg|png))', decoded_url)
    return filename_match.group(1) if filename_match else ''


def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)


def main():
    driver = create_driver()
    try:
        driver.get('https://instabooster.com.ua/divitis-storis-z-instagram-anonimno/')
        driver.find_element(By.CSS_SELECTOR, 'input#url').send_keys('tati_0904_')
        driver.find_element(By.CSS_SELECTOR, 'button.button').click()

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li.download-stories-preview--item'))
        )
        story_items = driver.find_elements(By.CSS_SELECTOR, 'li.download-stories-preview--item')
        print(f'Знайдено {len(story_items)} історій:')

        for idx, item in enumerate(story_items, 1):
            links = item.find_elements(By.CSS_SELECTOR, 'a')
            if links:
                href = links[0].get_attribute('href')
                filename = extract_filename_from_url(href)
                print(f'{idx}. {filename}\n {href}')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
