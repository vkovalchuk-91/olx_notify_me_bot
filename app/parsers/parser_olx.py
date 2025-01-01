import asyncio
import logging
import re

import httpx
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
HOST = 'https://www.olx.ua'


async def parse_latest_ads(url):
    latest_ads_url = await get_latest_ads_url(url)
    response_text_list = await get_one_page_response_text_list(latest_ads_url)
    return extract_ads(response_text_list)


async def get_latest_ads_url(url):
    latest_ads_query_text = 'search%5Border%5D=created_at%3Adesc'

    if 'search%5Border%5D=' in url:
        # Замінюємо текст, що відповідає шаблону, на нове значення
        # Шаблон для пошуку 'search%5Border%5D=' та тексту після нього до &
        pattern = r"search%5Border%5D=[^&]*"
        latest_ads_url = re.sub(pattern, latest_ads_query_text, url)
    elif '?' in url:
        # Якщо '?' є, додаємо значення після нього
        parts = url.split('?', 1)
        latest_ads_url = f"{parts[0]}?{latest_ads_query_text}&{parts[1]}"
    else:
        # Якщо '?' немає, додаємо значення в кінці з '?'
        latest_ads_url = f"{url}?{latest_ads_query_text}"
    return latest_ads_url


async def get_one_page_response_text_list(url):
    async with httpx.AsyncClient(headers=HEADERS) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return [response.text]
        else:
            logging.info(f'Response Error on {url}')
            return None


def parse_all_ads(url):
    responses_text_list = get_responses_text_list(url)
    return extract_ads(responses_text_list)


def get_responses_text_list(url):
    responses_text_list = []

    current_url = url
    while True:
        response = requests.get(current_url, headers=HEADERS)
        responses_text = response.text

        if response.status_code == 200:
            responses_text_list.append(responses_text)

            forward_page_url = get_pagination_forward_page_url_if_exist(responses_text)
            if forward_page_url:
                current_url = HOST + forward_page_url
            else:
                return responses_text_list
        else:
            logging.info(f'Response Error on {url}')
            return None


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
                        a_tag = ad_card_title.find('a', class_='css-qo0cxu')
                        if a_tag:
                            # Знайти url оголошення
                            url = a_tag['href']

                            if url not in unique_urls:  # Перевіряємо на дубляж
                                unique_urls.append(url)
                                ad_info['ad_url'] = HOST + url

                                # Знайти текст заголовка оголошення
                                ad_description = a_tag.find('h4', class_='css-1s3qyje').text
                                ad_info['ad_description'] = ad_description

                                # Знайти елемент 'p' з атрибутом 'data-testid="ad-price"' всередині ad_card_title
                                price_tag = ad_card_title.find('p', {'data-testid': 'ad-price'})
                                if price_tag:
                                    ad_info['ad_price'], ad_info['currency'] = split_price(price_tag.text)
                                else:
                                    ad_info['ad_price'], ad_info['currency'] = "0", "без ціни"

                    if ad_info:
                        unique_ads.append(ad_info)

    return unique_ads


def split_price(undivided_price):
    # Знаходимо індекс останнього пробілу
    last_space_index = undivided_price.rfind(' ')

    # Якщо пробіл не знайдено, повертаємо весь текст як валюту, а ціну залишаємо 0,
    # якщо ні розбиваємо текст на дві частини
    if last_space_index != -1:
        price = undivided_price[:last_space_index].replace(" ", "")
        currency = undivided_price[last_space_index + 1:]
    else:
        price = 0
        currency = undivided_price

    return price, currency


# def test():
#     url = 'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/?search%5Bdistrict_id%5D=13&search%5Bfilter_float_price:to%5D=8000&currency=UAH'
#     ads = parse_olx(url)
#     print(len(ads))
#     for ad in ads:
#         print(ad['ad_url'])
#
#
# if __name__ == '__main__':
#     test()

# async def test():
#     url = 'https://www.olx.ua/uk/list/q-%D1%84%D1%83%D1%82%D0%B7%D0%B0%D0%BB%D0%BA%D0%B8-43/?search%5Border%5D=filter_float_price:asc&search%5Bfilter_float_price:to%5D=1500'
#     ads = await parse_latest_ads(url)
#     print(len(ads))
#     # for ad in ads:
#     #     print(ad['ad_url'])
#
# if __name__ == '__main__':
#     asyncio.run(test())
