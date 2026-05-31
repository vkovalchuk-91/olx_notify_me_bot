from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Налаштовуємо headless режим
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)

try:
    driver.get("https://iqsaved.com/viewer/yulia.or.julia/")

    wait = WebDriverWait(driver, 60)

    # Чекаємо на появу елементів з контентом постів
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "div.profile-tabs__content-item.profile-tabs__posts ul.media-items")
    ))

    # Чекаємо на Сторіс (опційно, якщо вони є)
    stories_links = driver.find_elements(By.CSS_SELECTOR,
        "div.profile-tabs__content-item.profile-tabs__stories "
        "ul.media-items "
        "li.media-items__item "
        "div.media-items__info "
        "div.media-items__action "
        "a[download]"
    )

    print("Сторіс:")
    for i, link in enumerate(stories_links, 1):
        href = link.get_attribute("href")
        download = link.get_attribute("download")
        print(f"{i}. URL: {href}\n   Назва: {download}\n")

    # Чекаємо на пости
    posts_links = driver.find_elements(By.CSS_SELECTOR,
        "div.profile-tabs__content-item.profile-tabs__posts "
        "ul.media-items "
        "li.media-items__item "
        "div.media-items__info "
        "div.media-items__action "
        "a[download]"
    )

    print("Пости:")
    for i, link in enumerate(posts_links, 1):
        href = link.get_attribute("href")
        download = link.get_attribute("download")
        print(f"{i}. URL: {href}\n   Назва: {download}\n")

finally:
    driver.quit()
