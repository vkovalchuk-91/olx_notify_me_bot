import asyncio
import logging

from aiohttp import ClientSession, ClientConnectorError, InvalidURL
from bs4 import BeautifulSoup

HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
           'accept': '*/*'}
HOST = 'http://www.olx.ua'


class IncorrectURL(Exception):
    def __init__(self, message="Введений вами URL є некоректним"):
        self.message = message
        super().__init__(self.message)


async def parse_olx(url):
    responses_text_list = await get_responses_text_list(url)
    return extract_ads(responses_text_list)


async def get_responses_text_list(url):
    responses_text_list = []

    current_url = url
    async with ClientSession() as session:
        while True:
            async with session.get(current_url) as response:
                responses_text = await response.text()

                if response.status == 200:
                    responses_text_list.append(responses_text)

                    forward_page_url = get_pagination_forward_page_url_if_exist(responses_text)
                    if forward_page_url:
                        current_url = HOST + forward_page_url
                    else:
                        return responses_text_list
                else:
                    logging.info(f'Response Error on {url}')
                    return None


async def get_html(session: ClientSession, url, params=None):
    try:
        async with session.get(url, headers=HEADERS, params=params) as response:
            return response
    except (ClientConnectorError, InvalidURL):
        raise IncorrectURL()


def get_pagination_forward_page_url_if_exist(response_text):
    soup = BeautifulSoup(response_text, 'html.parser')
    try:
        listing_grid = soup.find_all('div', {'data-testid': 'listing-grid'})
        if len(listing_grid) > 1:  # Відсіюємо рекламні оголошення, якщо блоків більше 1
            return None
        next_page_url = soup.find('a', {'data-cy': 'pagination-forward'})['href']
        return next_page_url
    except TypeError:
        return None


def extract_ads(responses_text_list):
    unique_ads = []
    unique_urls = []

    if responses_text_list:
        for responses_text in responses_text_list:
            soup = BeautifulSoup(responses_text, 'html.parser')

            # Знайти перший елемент з data-testid="listing-grid"
            listing_grid = soup.find('div', {'data-testid': 'listing-grid'})

            if listing_grid:
                links = listing_grid.find_all('div', {'data-cy': 'l-card'})

                # Збираємо всі знайдені оголошення
                for link in links:
                    ad_info = {}

                    ad_card_title = link.find('div', {'data-cy': 'ad-card-title'})
                    if ad_card_title:
                        # Знайти елемент 'a' з класом 'css-z3gu2d' всередині ad_card_title
                        a_tag = ad_card_title.find('a', class_='css-z3gu2d')
                        if a_tag:
                            # Знайти url оголошення
                            url = a_tag['href']

                            if url not in unique_urls:  # Перевіряємо на дубляж
                                unique_urls.append(url)
                                ad_info['ad_url'] = HOST + url

                                # Знайти текст заголовка оголошення
                                ad_description = a_tag.find('h6', class_='css-1wxaaza').text
                                ad_info['ad_description'] = ad_description

                                # Знайти елемент 'p' з атрибутом 'data-testid="ad-price"' всередині ad_card_title
                                price_tag = ad_card_title.find('p', {'data-testid': 'ad-price'})
                                if price_tag:
                                    ad_info['ad_price'], ad_info['currency'] = split_price(price_tag.text)

                    if ad_info:
                        unique_ads.append(ad_info)

    return unique_ads


def split_price(undivided_price):
    # Знаходимо індекс останнього пробілу
    last_space_index = undivided_price.rfind(' ')

    # Якщо пробіл не знайдено, повертаємо весь текст як першу частину, а другу частину залишаємо порожньою
    if last_space_index == -1:
        return undivided_price, ''

    # Розбиваємо текст на дві частини
    price = undivided_price[:last_space_index]
    currency = undivided_price[last_space_index + 1:]

    return price, currency


async def test():
    # url = 'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/?search%5Bdistrict_id%5D=13&search%5Bfilter_float_price:to%5D=10000&currency=UAH'
    # url = 'https://www.olx.ua/uk/list/q-%D0%BF%D1%96%D0%B4%D0%BD%D0%BE%D0%B6%D0%BA%D0%B0-Cube/'
    url = 'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/?currency=UAH&search%5Bdistrict_id%5D=13'
    ads = await parse_olx(url)
    print(len(ads))
    # for ad in ads:
    #     print(ad['ad_url'])

if __name__ == '__main__':
    asyncio.run(test())
