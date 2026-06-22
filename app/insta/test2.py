import asyncio
from playwright.async_api import async_playwright


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://iqsaved.com/viewer/yulia.or.julia/", timeout=600000)

        # Чекаємо на появу контенту з stories
        await page.mouse.wheel(0, 1000)
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("li.media-items__item", timeout=600000)

        # await page.wait_for_selector("li.media-items__item", state="attached", timeout=600000)

        # html = await page.content()
        # print(html)

        # Локатор для всіх <a> всередині li сторісів
        stories_locator = page.locator(
            "div.profile-tabs__content-item.profile-tabs__stories "
            "ul.media-items "
            "li.media-items__item "
            "div.media-items__info "
            "div.media-items__action "
            "a[download]"
        )

        # Витягуємо всі пари href + download
        links = await stories_locator.evaluate_all(
            "elements => elements.map(el => ({ href: el.href, download: el.download }))"
        )

        # Виводимо результат
        for i, link in enumerate(links, 1):
            print(f"{i}. URL: {link['href']}\n   Назва: {link['download']}\n")

        # Локатор для всіх <a> всередині li постів
        posts_locator = page.locator(
            "div.profile-tabs__content-item.profile-tabs__posts "
            "ul.media-items "
            "li.media-items__item "
            "div.media-items__info "
            "div.media-items__action "
            "a[download]"
        )

        # Витягуємо всі пари href + download
        links = await posts_locator.evaluate_all(
            "elements => elements.map(el => ({ href: el.href, download: el.download }))"
        )

        # Виводимо результат
        for i, link in enumerate(links, 1):
            print(f"{i}. URL: {link['href']}\n   Назва: {link['download']}\n")

        await browser.close()


asyncio.run(run())
