import asyncio
import logging
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import os

import httpx
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USE_ASYNC_MODE = os.getenv('USE_ASYNC_MODE', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
WORKERS_NUMBER = int(os.getenv('WORKERS_NUMBER', '1'))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/128.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive',
}
HOST = 'https://www.olx.ua'


async def get_parsed_ads(olx_checker_queries: Dict[int, str]) -> Dict[int, List[Dict]]:
    logger.info(
        'OLX scraper: starting fetch for %s queries. Async mode=%s, workers=%s',
        len(olx_checker_queries),
        USE_ASYNC_MODE,
        WORKERS_NUMBER if USE_ASYNC_MODE else 1,
        extra={'job_name': 'check_new_ads'},
    )
    if USE_ASYNC_MODE:
        queries_with_responses_text = await get_responses_text_with_async_mode(olx_checker_queries)
    else:
        queries_with_responses_text = get_responses_text_with_sync_mode(olx_checker_queries)
    parsed_ads = extract_ads(queries_with_responses_text)
    logger.info(
        'OLX scraper: finished. Parsed %s ads from %s queries',
        sum(len(ads) for ads in parsed_ads.values()),
        len(parsed_ads),
        extra={'job_name': 'check_new_ads'},
    )
    return parsed_ads


async def get_responses_text_with_async_mode(olx_checker_queries: Dict[int, str]) -> Dict[int, List[str]]:
    queue = asyncio.Queue()
    queries_with_responses_text = {}
    queued_urls = {}

    for query_id, query_url in olx_checker_queries.items():
        queued_urls[query_id] = {query_url}
        await queue.put((query_id, query_url, 1))

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        workers = [
            asyncio.create_task(worker(queue, client, queries_with_responses_text, queued_urls))
            for _ in range(WORKERS_NUMBER)
        ]
        await queue.join()
        for _ in range(WORKERS_NUMBER):
            await queue.put(None)
        await asyncio.gather(*workers)
    return queries_with_responses_text


async def worker(queue, client, queries_with_responses_text, queued_urls):
    while True:
        query = await queue.get()
        if query is None:
            break
        await fetch_url_with_async_mode(client, query, queue, queries_with_responses_text, queued_urls)
        queue.task_done()


async def fetch_url_with_async_mode(client, query, queue, queries_with_responses_text, queued_urls):
    query_id = query[0]
    url = query[1]
    page_number = query[2]
    try:
        response = await client.get(url)
        if response.status_code != 200:
            logger.warning(
                'OLX scraper: received HTTP %s for query_id=%s page=%s %s',
                response.status_code,
                query_id,
                page_number,
                url,
                extra={'job_name': 'check_new_ads'},
            )
            return

        queries_with_responses_text.setdefault(query_id, []).append(response.text)
        logger.info(
            'OLX scraper: fetched query_id=%s page=%s successfully: %s',
            query_id,
            page_number,
            url,
            extra={'job_name': 'check_new_ads'},
        )
        for pagination_page_number, pagination_url in get_pagination_page_urls(response.text):
            if pagination_url in queued_urls.setdefault(query_id, set()):
                continue
            queued_urls[query_id].add(pagination_url)
            await queue.put((query_id, pagination_url, pagination_page_number))
            logger.info(
                'OLX scraper: queued query_id=%s page=%s from pagination: %s',
                query_id,
                pagination_page_number,
                pagination_url,
                extra={'job_name': 'check_new_ads'},
            )
    except Exception as exc:
        logger.warning(
            'OLX scraper: failed to fetch query_id=%s page=%s %s: %s',
            query_id,
            page_number,
            url,
            exc,
            extra={'job_name': 'check_new_ads'},
        )


def get_responses_text_with_sync_mode(olx_checker_queries: Dict[int, str]) -> Dict[int, List[str]]:
    queries_with_responses_text = {}
    for query_id, query_url in olx_checker_queries.items():
        current = fetch_url_with_sync_mode((query_id, query_url))
        if current:
            queries_with_responses_text.setdefault(query_id, []).extend(current[query_id])
    return queries_with_responses_text


def fetch_url_with_sync_mode(query: Tuple[int, str]):
    queries_with_responses_text = {}
    query_id = query[0]
    queued_pages = [(1, query[1])]
    queued_urls = {query[1]}
    processed_urls = set()
    while queued_pages:
        page_number, current_url = queued_pages.pop(0)
        if current_url in processed_urls:
            continue
        processed_urls.add(current_url)
        response = requests.get(current_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            logger.info(
                'OLX scraper: fetched query_id=%s page=%s successfully: %s',
                query_id,
                page_number,
                current_url,
                extra={'job_name': 'check_new_ads'},
            )
            queries_with_responses_text.setdefault(query_id, []).append(response.text)
            for pagination_page_number, pagination_url in get_pagination_page_urls(response.text):
                if pagination_url in queued_urls:
                    continue
                queued_urls.add(pagination_url)
                queued_pages.append((pagination_page_number, pagination_url))
                logger.info(
                    'OLX scraper: queued query_id=%s page=%s from pagination: %s',
                    query_id,
                    pagination_page_number,
                    pagination_url,
                    extra={'job_name': 'check_new_ads'},
                )
        else:
            logger.warning(
                'OLX scraper: received HTTP %s for query_id=%s page=%s %s',
                response.status_code,
                query_id,
                page_number,
                current_url,
                extra={'job_name': 'check_new_ads'},
            )
            return None
    return queries_with_responses_text


def get_pagination_page_urls(response_text: str) -> List[Tuple[int, str]]:
    soup = BeautifulSoup(response_text, 'html.parser')
    listing_grid = soup.find_all('div', {'data-testid': 'listing-grid'})
    if len(listing_grid) > 1:
        return []

    pagination_urls = {}
    for link in soup.find_all('a', href=True):
        href = link['href']
        data_cy = link.get('data-cy', '')
        data_testid = link.get('data-testid', '')
        is_pagination_link = (
            'page=' in href
            or 'pagination' in data_cy
            or 'pagination' in data_testid
        )
        if not is_pagination_link:
            continue

        page_url = urljoin(HOST, href)
        page_number = _get_page_number(page_url, link.get_text(strip=True))
        if not page_number:
            continue
        pagination_urls[page_url] = page_number

    return sorted(
        ((page_number, page_url) for page_url, page_number in pagination_urls.items()),
        key=lambda item: item[0],
    )


def _get_page_number(page_url: str, fallback_text: str = '') -> int | None:
    query_params = parse_qs(urlparse(page_url).query)
    page_values = query_params.get('page', [])
    if page_values and page_values[0].isdigit():
        return int(page_values[0])
    return int(fallback_text) if fallback_text.isdigit() else None


def extract_ads(queries_with_responses_text: Dict[int, List[str]]) -> Dict[int, List[Dict]]:
    queries_with_unique_ads = {}
    if not queries_with_responses_text:
        return queries_with_unique_ads

    for query_id, responses_text in queries_with_responses_text.items():
        unique_urls = []
        queries_with_unique_ads[query_id] = []
        for response_text in responses_text:
            soup = BeautifulSoup(response_text, 'html.parser')
            listing_grid = soup.find('div', {'data-testid': 'listing-grid'})
            if not listing_grid:
                continue
            for link in listing_grid.find_all('div', {'data-cy': 'l-card'}):
                ad_info = {}
                ad_card_title = link.find('div', {'data-cy': 'ad-card-title'})
                if not ad_card_title:
                    continue
                a_tag = ad_card_title.find('a')
                if not a_tag:
                    continue
                url = HOST + a_tag['href']
                if url in unique_urls or 'olx.ua/d/obyavlenie' in url:
                    continue
                unique_urls.append(url)
                ad_info['ad_url'] = url
                ad_info['ad_description'] = a_tag.find('h4').text
                price_tag = ad_card_title.find('p', {'data-testid': 'ad-price'})
                if price_tag:
                    ad_info['ad_price'], ad_info['currency'] = split_price(price_tag.text)
                else:
                    ad_info['ad_price'], ad_info['currency'] = 0, 'без ціни'
                queries_with_unique_ads[query_id].append(ad_info)
    return queries_with_unique_ads


def split_price(undivided_price: str) -> Tuple:
    last_space_index = undivided_price.rfind(' ')
    if last_space_index != -1:
        price = undivided_price[:last_space_index].replace(' ', '')
        currency = undivided_price[last_space_index + 1:]
    else:
        price = 0
        currency = undivided_price
    return price, currency
