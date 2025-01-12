import asyncio
import logging
import os
from typing import Dict, List, Tuple

import httpx
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Loading variables from the .env file
load_dotenv()
USE_ASYNC_MODE = os.getenv("USE_ASYNC_MODE", "false").lower() in ["true", "1", "t", "y", "yes"]
WORKERS_NUMBER = int(os.getenv("WORKERS_NUMBER"))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/128.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
HOST = 'https://www.olx.ua'


async def get_parsed_ads(olx_checker_queries: Dict[int, str]) -> Dict[int, List[Dict]]:
    if USE_ASYNC_MODE:
        queries_with_responses_text = await get_responses_text_with_async_mode(olx_checker_queries)
    else:
        queries_with_responses_text = get_responses_text_with_sync_mode(olx_checker_queries)
    return extract_ads(queries_with_responses_text)


async def get_responses_text_with_async_mode(olx_checker_queries: Dict[int, str]) -> Dict[int, List[str]]:
    queue = asyncio.Queue()
    queries_with_responses_text = {}

    # Додаємо початкові URL у чергу
    for query_id, query_url in olx_checker_queries.items():
        await queue.put((query_id, query_url))

    async with httpx.AsyncClient(headers=HEADERS) as client:
        # Створюємо воркери
        workers = [asyncio.create_task(worker(queue, client, queries_with_responses_text))
                   for _ in range(WORKERS_NUMBER)]

        # Чекаємо, поки всі завдання будуть виконані
        await queue.join()

        # Завершуємо воркерів
        for _ in range(WORKERS_NUMBER):
            await queue.put(None)  # Спеціальний сигнал завершення

        await asyncio.gather(*workers)
    return queries_with_responses_text


async def worker(
        queue: asyncio.Queue,
        client: httpx.AsyncClient,
        queries_with_responses_text: Dict[int, List[str]]
):
    """Асинхронний воркер, який обробляє завдання з черги."""
    while True:
        query = await queue.get()
        if query is None:  # Спеціальний сигнал для завершення
            break
        await fetch_url_with_async_mode(client, query, queue, queries_with_responses_text)
        queue.task_done()


async def fetch_url_with_async_mode(
        client: httpx.AsyncClient,
        query: Tuple[int, str],
        queue: asyncio.Queue,
        queries_with_responses_text: Dict[int, List[str]]
):
    """Функція для завантаження URL і динамічного додавання нових завдань."""
    query_id = query[0]
    url = query[1]
    try:
        response = await client.get(url)
        if response.status_code == 200:
            if query_id not in queries_with_responses_text:
                queries_with_responses_text[query_id] = []
            queries_with_responses_text[query_id].append(response.text)

        forward_page_url = get_pagination_forward_page_url_if_exist(response.text)
        # Динамічно додаємо нові URL
        if forward_page_url:
            await queue.put((query_id, forward_page_url))  # Додаємо item з новим URL у чергу
    except Exception as e:
        logging.info(f"Error fetching {url}: {e}")


def get_responses_text_with_sync_mode(olx_checker_queries: Dict[int, str]) -> Dict[int, List[str]]:
    queries_with_responses_text = {}
    for query_id, query_url in olx_checker_queries.items():
        current_query_with_responses_text = fetch_url_with_sync_mode((query_id, query_url))
        if query_id not in queries_with_responses_text:
            queries_with_responses_text[query_id] = []
        queries_with_responses_text[query_id] += current_query_with_responses_text[query_id]
    return queries_with_responses_text


def fetch_url_with_sync_mode(query: Tuple[int, str]) -> Dict[int, List[str]] | None:
    queries_with_responses_text = {}

    query_id = query[0]
    current_url = query[1]
    while True:
        response = requests.get(current_url, headers=HEADERS)
        responses_text = response.text

        if response.status_code == 200:
            logging.info(f"Fetched {current_url}...: {response.status_code}")
            if query_id not in queries_with_responses_text:
                queries_with_responses_text[query_id] = []
            queries_with_responses_text[query_id].append(response.text)

            forward_page_url = get_pagination_forward_page_url_if_exist(responses_text)
            if forward_page_url:
                current_url = forward_page_url
            else:
                return queries_with_responses_text
        else:
            logging.info(f'Response Error on {current_url}')
            return None


def get_pagination_forward_page_url_if_exist(response_text: str) -> None | str:
    soup = BeautifulSoup(response_text, 'html.parser')
    try:
        listing_grid = soup.find_all('div', {'data-testid': 'listing-grid'})
        if len(listing_grid) > 1:  # Відсіюємо рекламні оголошення, якщо блоків більше 1
            return None
        next_page_url = soup.find('a', {'data-cy': 'pagination-forward'})['href']
        return HOST + next_page_url
    except TypeError:
        return None


def extract_ads(queries_with_responses_text: Dict[int, List[str]]) -> Dict[int, List[Dict]]:
    queries_with_unique_ads = {}

    if queries_with_responses_text:
        for query_id, responses_text in queries_with_responses_text.items():
            unique_urls = []
            for response_text in responses_text:
                queries_with_unique_ads[query_id] = []
                soup = BeautifulSoup(response_text, 'html.parser')

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
                                url = HOST + a_tag['href']

                                # Перевіряємо на дубляж та задвоєння через "olx.ua/d/obyavlenie"
                                if url not in unique_urls and "olx.ua/d/obyavlenie" not in url:
                                    unique_urls.append(url)
                                    ad_info['ad_url'] = url

                                    # Знайти текст заголовка оголошення
                                    ad_description = a_tag.find('h4', class_='css-1s3qyje').text
                                    ad_info['ad_description'] = ad_description

                                    # Знайти елемент 'p' з атрибутом 'data-testid="ad-price"' всередині ad_card_title
                                    price_tag = ad_card_title.find('p', {'data-testid': 'ad-price'})
                                    if price_tag:
                                        ad_info['ad_price'], ad_info['currency'] = split_price(price_tag.text)
                                    else:
                                        ad_info['ad_price'], ad_info['currency'] = 0, "без ціни"

                        if ad_info:
                            queries_with_unique_ads[query_id].append(ad_info)
    return queries_with_unique_ads


def split_price(undivided_price: str) -> Tuple[int, str]:
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


async def test():
    queries = {
        1: 'https://www.olx.ua/uk/list/q-%D0%AF-%D0%B1%D0%B0%D1%87%D1%83-%D0%B2%D0%B0%D1%81-%D1%86%D1%96%D0%BA%D0%B0%D0'
           '%B2%D0%B8%D1%82%D1%8C-%D0%BF%D1%96%D1%82%D1%8C%D0%BC%D0%B0/?search%5Bfilter_float_price:to%5D=250',
        2: 'https://www.olx.ua/uk/dom-i-sad/mebel/ofisnaya-mebel/q-%D1%81%D1%82%D1%96%D0%BB-%D1%80%D0%BE%D0%B7%D0%BA%D0'
           '%BB%D0%B0%D0%B4%D0%BD%D0%B8%D0%B9/?currency=UAH&search%5Bfilter_float_price:to%5D=1200',
        3: 'https://www.olx.ua/uk/cherkassy/q-%D0%B1%D1%83%D1%82%D1%8B%D0%BB%D1%8C/?min_id=854431324&reason='
           'observed_search',
        4: 'https://www.olx.ua/uk/list/q-%D0%B1%D0%B0%D0%BC%D0%BF%D0%B8-43/?search%5Bfilter_float_price:to%5D=1500',
        5: 'https://www.olx.ua/uk/list/q-%D0%BA%D0%BE%D0%BF%D0%BE%D1%87%D0%BA%D0%B8-43/?search%5Bfilter_float_price:'
           'to%5D=1500',
        6: 'https://www.olx.ua/uk/list/q-Повісті-дикого-степу/',
        7: 'https://www.olx.ua/uk/cherkassy/q-%D0%B1%D1%83%D1%82%D0%BB%D1%8C/?min_id=853718254&reason=observed_search&'
           'search%5Border%5D=filter_float_price%3Aasc',
        8: 'https://www.olx.ua/uk/cherkassy/q-%D0%B1%D1%83%D1%82%D0%B8%D0%BB%D1%8C/?min_id=855940298&reason='
           'observed_search',
        9: 'https://www.olx.ua/uk/cherkassy/q-%D0%B1%D1%83%D1%82%D0%B5%D0%BB%D1%8C/?min_id=855940298&reason='
           'observed_search',
        10: 'https://www.olx.ua/uk/list/q-Usams-T20/',
        11: 'https://www.olx.ua/uk/list/q-%D1%84%D1%83%D1%82%D0%B7%D0%B0%D0%BB%D0%BA%D0%B8-43/?search%5B'
            'filter_float_price%3Ato%5D=1500',
        12: 'https://www.olx.ua/uk/list/q-юпак/',
        13: 'https://www.olx.ua/uk/list/q-Кіно-дикого-степу/',
        14: 'https://www.olx.ua/uk/list/q-Всьо-чотко/',
    }
    queries_with_unique_ads = await get_parsed_ads(queries)
    print(len(queries_with_unique_ads))
    for query_id, adds in queries_with_unique_ads.items():
        print(f'{query_id}: found {len(adds)} adds')

if __name__ == '__main__':
    asyncio.run(test())
