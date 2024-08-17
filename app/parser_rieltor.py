import logging

import requests
from bs4 import BeautifulSoup
from requests.exceptions import MissingSchema, ConnectionError

HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
           'accept': '*/*'}
HOST = 'https://rieltor.ua'


class IncorrectURL(Exception):
    def __init__(self, message="Введений вами URL є некоректним"):
        self.message = message
        super().__init__(self.message)


def parse_rieltor(url):
    responses_text_list = get_responses_text_list(url)
    return extract_ads(responses_text_list)


def get_responses_text_list(url):
    responses_text_list = []
    unique_next_page_urls = []

    current_url = url
    while True:
        response = get_html(current_url)
        if response.status_code == 200:
            forward_page_url = get_pagination_forward_page_url_if_exist(response)

            # Перевіряємо чи посилання на наступну сторінку є унікальним й до цього не було доданим в список тих, по
            # яким вже здійснювався запит
            if forward_page_url:
                if forward_page_url in unique_next_page_urls:
                    return responses_text_list
                else:
                    unique_next_page_urls.append(forward_page_url)

            responses_text_list.append(response.text)
            if forward_page_url:
                current_url = forward_page_url
            else:
                return responses_text_list
        else:
            logging.info(f'Response Error on {url}')
            return None


def get_pagination_forward_page_url_if_exist(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    try:
        pagination_elements = soup.find('ul', class_='pagination_custom')
        if pagination_elements:
            find_next_page_url = False
            for li in pagination_elements.find_all('li'):
                if find_next_page_url:
                    next_page_url = HOST + li.find('a', class_='pager-btn')['href']
                    return next_page_url
                if 'active' in li.get('class', []):
                    find_next_page_url = True
            return None
        else:
            return None
    except TypeError:
        return None


def get_html(url, params=None):
    try:
        req = requests.get(url, headers=HEADERS, params=params)
        return req
    except (ConnectionError, MissingSchema):
        raise IncorrectURL()


def extract_ads(responses_text_list):
    unique_ads = []
    unique_urls = []

    if responses_text_list:
        for responses_text in responses_text_list:
            soup = BeautifulSoup(responses_text, 'html.parser')
            # Знайти перший елемент з data-testid="listing-grid"
            offers_raw = soup.find('div', class_='container-offers').find('div', class_='row')

            if offers_raw:
                cards = offers_raw.find_all('div', class_='catalog-card')

                # Збираємо всі знайдені оголошення
                for card in cards:
                    ad_info = {}

                    a_tag = card.find('a', class_='catalog-card-media')
                    url = a_tag['href']
                    if url not in unique_urls:  # Перевіряємо на дубляж
                        unique_urls.append(url)
                        ad_info['ad_url'] = a_tag['href']

                        price = card.get('data-label')
                        ad_info['ad_price'], ad_info['currency'] = split_price(price)

                        a_tag = card.find('a', class_='catalog-card-media')
                        ad_info['ad_url'] = a_tag['href']

                        region_tag = card.find('div', class_='catalog-card-region')
                        region_details = region_tag.find_all('a', {'data-analytics-event': 'card-click-region'})
                        address_tag = card.find('div', class_='catalog-card-address')
                        city = region_details[0].text.strip()
                        district = region_details[1].text.strip()
                        address = address_tag.text.strip()
                        ad_info['ad_description'] = f'{city}, {district}, {address}'

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


# ads = parse('https://rieltor.ua/flats-rent/1-room/?district%5B0%5D=76&district%5B1%5D=82&district%5B2%5D=78&district%5B3%5D=86&district%5B4%5D=80&district%5B5%5D=79&price_max=10000&radius=20&sort=bycreated#11.69/50.4692/30.4294')
# print(len(ads))
# for ad in ads:
#     print(ad)

ads = parse_rieltor('https://rieltor.ua/flats-rent/1-room/?district%5B0%5D=76&district%5B1%5D=82&district%5B2%5D=78&district%5B3%5D=86&district%5B4%5D=80&district%5B5%5D=79&price_max=6000&radius=20&sort=bycreated#10.22/50.4654/30.4495')
print(len(ads))
for ad in ads:
    print(ad)

# ads = parse('https://rieltor.ua/flats-rent/1-room/?district%5B0%5D=76&district%5B1%5D=82&district%5B2%5D=78&district%5B3%5D=86&district%5B4%5D=80&district%5B5%5D=79&radius=20&sort=bycreated')
# print(len(ads))
# for ad in ads:
#     print(ad)
