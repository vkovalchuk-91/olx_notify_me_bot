import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}
HOST = 'http://www.olx.ua'


class IncorrectURL(Exception):
    def __init__(self, message="Введений вами URL є некоректним"):
        self.message = message
        super().__init__(self.message)


def parse_olx(url):
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
            print(f'Response Error on {url}')
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

    # Якщо пробіл не знайдено, повертаємо весь текст як першу частину, а другу частину залишаємо порожньою
    if last_space_index == -1:
        return undivided_price, ''

    # Розбиваємо текст на дві частини
    price = undivided_price[:last_space_index]
    currency = undivided_price[last_space_index + 1:]

    return price, currency


def test():
    url = 'https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/?search%5Bdistrict_id%5D=13&search%5Bfilter_float_price:to%5D=8000&currency=UAH'
    ads = parse_olx(url)
    print(len(ads))
    for ad in ads:
        print(ad['ad_url'])


if __name__ == '__main__':
    test()
