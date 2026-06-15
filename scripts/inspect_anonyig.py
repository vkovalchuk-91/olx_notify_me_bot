from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


URLS = [
    'https://anonyig.com/en/',
    'https://anonyig.com/en/instagram/testuser',
    'https://anonyig.com/en/profile/testuser',
    'https://anonyig.com/en/viewer/testuser',
]


def create_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    return webdriver.Chrome(options=options)


def inspect_page(driver, url: str) -> None:
    print('---', url)
    driver.get(url)
    print('url', driver.current_url)
    print('title', driver.title)
    inputs = [
        {
            'placeholder': element.get_attribute('placeholder'),
            'name': element.get_attribute('name'),
            'type': element.get_attribute('type'),
            'id': element.get_attribute('id'),
            'className': element.get_attribute('class'),
        }
        for element in driver.find_elements(By.CSS_SELECTOR, 'input, textarea')
    ]
    print('inputs', inputs)
    controls = [
        {
            'tag': element.tag_name,
            'text': element.text[:80],
            'src': element.get_attribute('src'),
            'className': element.get_attribute('class'),
            'action': element.get_attribute('action'),
        }
        for element in driver.find_elements(By.CSS_SELECTOR, 'button, img[src*="search"], [type="submit"], form')
    ]
    print('buttons/forms', controls[:20])
    print('media_items', len(driver.find_elements(By.CSS_SELECTOR, 'li.profile-media-list__item')))
    html = driver.page_source
    Path('/tmp/anonyig.html').write_text(html[:50000], encoding='utf-8')
    print('html_saved', min(len(html), 50000))


def main():
    driver = create_driver()
    try:
        for url in URLS:
            try:
                inspect_page(driver, url)
            except Exception as exc:
                print('error', exc)
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
