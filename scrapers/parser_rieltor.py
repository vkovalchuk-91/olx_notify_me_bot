import asyncio
import logging
from urllib.parse import urljoin

from aiohttp import ClientSession
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
REQUEST_DELAY_SECONDS = 1
RETRY_DELAY_SECONDS = 5

HEADERS = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
    'accept': '*/*',
}
HOST = 'https://rieltor.ua'


async def parse_rieltor(url):
    logger.info('Rieltor scraper: starting fetch for %s', url, extra={'job_name': 'check_new_ads'})
    responses_text_list = await get_responses_text_list(url)
    ads = extract_ads(responses_text_list)
    logger.info(
        'Rieltor scraper: finished %s. Parsed %s ads',
        url,
        len(ads),
        extra={'job_name': 'check_new_ads'},
    )
    return ads


async def get_responses_text_list(url):
    responses_text_list = []
    current_url = url
    page_number = 1
    async with ClientSession() as session:
        while True:
            responses_text = await _fetch_page(session, current_url, page_number)
            if responses_text is None:
                if responses_text_list:
                    logger.warning(
                        'Rieltor scraper: stopped pagination at page=%s %s after %s fetched page(s). '
                        'Using ads collected before the failed page.',
                        page_number,
                        current_url,
                        len(responses_text_list),
                        extra={'job_name': 'check_new_ads'},
                    )
                    return responses_text_list
                return []

            responses_text_list.append(responses_text)
            logger.info(
                'Rieltor scraper: fetched page=%s successfully: %s',
                page_number,
                current_url,
                extra={'job_name': 'check_new_ads'},
            )
            forward_page_url = get_pagination_forward_page_url_if_exist(responses_text)
            if forward_page_url:
                current_url = forward_page_url
                page_number += 1
                await asyncio.sleep(REQUEST_DELAY_SECONDS)
            else:
                return responses_text_list


async def _fetch_page(session, current_url, page_number):
    for attempt in range(MAX_RETRIES + 1):
        async with session.get(current_url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.text()

            if response.status == 429 and attempt < MAX_RETRIES:
                delay_seconds = RETRY_DELAY_SECONDS * (attempt + 1)
                logger.warning(
                    'Rieltor scraper: received HTTP 429 for page=%s %s. Retrying in %s seconds '
                    '(attempt %s/%s).',
                    page_number,
                    current_url,
                    delay_seconds,
                    attempt + 1,
                    MAX_RETRIES,
                    extra={'job_name': 'check_new_ads'},
                )
                await asyncio.sleep(delay_seconds)
                continue

            logger.warning(
                'Rieltor scraper: received HTTP %s for page=%s %s',
                response.status,
                page_number,
                current_url,
                extra={'job_name': 'check_new_ads'},
            )
            return None

    return None


def get_pagination_forward_page_url_if_exist(responses_text):
    soup = BeautifulSoup(responses_text, 'html.parser')
    try:
        pagination_elements = soup.find('ul', class_='pagination_custom')
        if not pagination_elements:
            return None
        find_next_page_url = False
        for li in pagination_elements.find_all('li'):
            if find_next_page_url:
                return urljoin(HOST, li.find('a', class_='pager-btn')['href'])
            if 'active' in li.get('class', []):
                find_next_page_url = True
        return None
    except (TypeError, KeyError):
        return None


def extract_ads(responses_text_list):
    unique_ads = []
    unique_urls = []
    if not responses_text_list:
        return unique_ads

    for responses_text in responses_text_list:
        soup = BeautifulSoup(responses_text, 'html.parser')
        for card in soup.find_all('div', class_='catalog-card'):
            a_tag = card.find('a', class_='catalog-card-media')
            if not a_tag:
                continue
            url = urljoin(HOST, a_tag['href'])
            if url in unique_urls:
                continue
            unique_urls.append(url)
            price = _get_text(card, 'div.catalog-card-price') or card.get('data-label', '')
            ad_price, currency = split_price(price)
            region_tag = card.find('div', class_='catalog-card-region')
            region_details = region_tag.find_all('a', {'data-analytics-event': 'card-click-region'}) if region_tag else []
            city = region_details[0].text.strip() if region_details else ''
            district = region_details[1].text.strip() if len(region_details) == 2 else ''
            address = _get_text(card, 'div.catalog-card-address')
            unique_ads.append({
                'ad_url': url,
                'ad_description': f'{city}, {district}, {address}'.strip(', '),
                'ad_price': ad_price,
                'currency': currency,
            })
    return unique_ads


def _get_text(card, selector: str) -> str:
    element = card.select_one(selector)
    return element.get_text(' ', strip=True) if element else ''


def split_price(undivided_price):
    undivided_price = undivided_price.replace('/міс', '').strip()
    last_space_index = undivided_price.rfind(' ')
    if last_space_index == -1:
        return undivided_price, ''
    return undivided_price[:last_space_index], undivided_price[last_space_index + 1:]
