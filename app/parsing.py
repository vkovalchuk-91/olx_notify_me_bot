import requests
from bs4 import BeautifulSoup
URL = ('https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/?search%5Bdistrict_id%5D=9'
       '&search%5Bfilter_float_price:from%5D=5000&search%5Bfilter_float_price:to%5D=8000&currency=UAH')
HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
           'accept': '*/*'}
HOST = 'http://www.olx.ua'


def get_html(url, params=None):
    req = requests.get(url, headers=HEADERS, params=params)
    return req


def print_content(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    # Знайти перший елемент з data-testid="listing-grid"
    listing_grid = soup.find('div', {'data-testid': 'listing-grid'})

    if listing_grid:
        links = listing_grid.find_all('div', {'data-cy': 'l-card'})

        # Друкуємо всі знайдені посилання
        for link in links:
            ad_card_title = link.find('div', {'data-cy': 'ad-card-title'})

            if ad_card_title:
                # Знайти елемент 'a' з класом 'css-z3gu2d' всередині ad_card_title
                a_tag = ad_card_title.find('a', class_='css-z3gu2d')
                if a_tag:
                    # Знайти текст заголовка оголошення
                    ad_title = a_tag.find('h6', class_='css-1wxaaza').text
                    print('Заголовок оголошення:', ad_title)

                    # Знайти url оголошення
                    url = a_tag['href']
                    print('URL оголошення:', HOST + url)

                # Знайти елемент 'p' з атрибутом 'data-testid="ad-price"' всередині ad_card_title
                price_tag = ad_card_title.find('p', {'data-testid': 'ad-price'})
                if price_tag:
                    price = price_tag.text
                    print('Ціна оголошення:', price)

                print()
            else:
                print("Елемент з data-cy='ad-card-title' не знайдено.")


def parse():
    response = get_html(URL)
    if response.status_code == 200:
        print_content(response)
    else:
        print('Error')


parse()
