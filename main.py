import pickle
import re
import sys
from random import randint
from time import sleep as pause
from time import time

from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from converter import *


def get_all_notebook_urls(driver) -> list[str]:
    """
    Собирает все ссылки на ноутбуки из всех страниц с ними.
    """
    page = 1
    url_template = 'https://www.dns-shop.ru/catalog/17a892f816404e77/noutbuki/?f[p3q]=b3ci&p={page}'

    url = url_template.format(page=page)
    driver.get(url=url)
    pause(10)

    set_city(driver, 'Краснодар')

    urls = []
    while page_urls := get_urls_from_page(driver):
        print(f'Страница {page}')

        urls.extend(page_urls)

        url = url_template.format(page=page)

        page += 1

        driver.get(url)

        pause(randint(6, 9))
    return urls


def set_city(driver, city: str) -> None:
    """
    Выбирает на сайте переданный город.
    """
    pause(7)
    driver.find_element(
        By.CLASS_NAME,
        "header-top-menu__common-link.header-top-menu__common-link_city"
    ).click()
    pause(7)
    city_input = driver.find_element(
        By.CLASS_NAME,
        'base-ui-input-search__input'
    )
    city_input.clear()
    city_input.send_keys(city)
    pause(1)
    driver.find_element(By.CSS_SELECTOR, 'ul.cities-search > li').click()
    pause(10)


def get_urls_from_page(driver) -> list[str]:
    """
    Собирает все ссылки на ноутбуки из текущей страницы.
    """
    soup = BeautifulSoup(driver.page_source, 'lxml')
    elements = soup.find_all('a', class_="catalog-product__name ui-link ui-link_black")
    return list(map(
        lambda element: 'https://www.dns-shop.ru' + element.get("href") + 'characteristics/',
        elements
    ))


def get_notebook_data(driver, url: str) -> dict[str, str | int]:
    """
    Собирает информацию о ноутбуке по ссылке.
    """
    notebook = dict()

    driver.get(url)
    pause(5)

    soup = BeautifulSoup(driver.page_source, 'lxml')

    model = find_if_on_page(r'Модель', soup)

    notebook["Производитель"], notebook["Модель"] = re.search(
        r"(Dream Machines|.+?) (.+)",
        model
    ).group(1, 2)

    notebook["Операционная система"] = find_if_on_page(r'Операционная система', soup)

    screen_type = find_if_on_page(r'Тип экрана', soup)
    screen_diagonal = find_if_on_page(r'Диагональ экрана \(дюйм\)', soup)
    screen_resolution = re.search(
        r'(\d+x\d+)',
        find_if_on_page(r'Разрешение экрана', soup)
    ).group(1)
    max_screen_refresh_rate = find_if_on_page(
        r'Максимальная частота обновления экрана',
        soup
    )
    notebook["Экран"] = f"{screen_resolution} " \
                        f"{screen_diagonal} " \
                        f"{screen_type} " \
                        f"{max_screen_refresh_rate}"

    cpu_model = find_if_on_page(r'Модель процессора', soup)
    number_of_performance_cores = find_if_on_page(
        r'Количество производительных ядер',
        soup
    )
    cpu_frequency = find_if_on_page(r'Частота процессора', soup)
    if cpu_frequency != 'Нет':
        notebook["Процессор"] = f"{cpu_model} " \
                                f"{number_of_performance_cores}x{cpu_frequency}"
    else:
        notebook["Процессор"] = f"{cpu_model} " \
                                f"кол-во ядер: {number_of_performance_cores}"

    ram_type = find_if_on_page(r'Тип оперативной памяти', soup)
    amount_of_ram = find_if_on_page(r'Объем оперативной памяти', soup)
    ram_frequency = find_if_on_page(r'Частота оперативной памяти', soup)
    if ram_frequency != 'Нет':
        notebook["Оперативная память"] = f"{amount_of_ram} " \
                                         f"{ram_type} " \
                                         f"{ram_frequency}"
    else:
        notebook["Оперативная память"] = f"{amount_of_ram} {ram_type}"

    notebook["Встроенная видеокарта"] = find_if_on_page(
        r'Модель встроенной видеокарты',
        soup
    )

    built_in_video_card_model = find_if_on_page(
        r'Модель дискретной видеокарты',
        soup
    )
    video_chip_manufacturer = find_if_on_page(
        r'Производитель видеочипа',
        soup
    )
    video_memory_size = find_if_on_page(r'Объем видеопамяти', soup)
    notebook["Дискретная видеокарта"] = f"{video_chip_manufacturer} " \
                                        f"{built_in_video_card_model} " \
                                        f"{video_memory_size}"

    total_ssd_size = find_if_on_page(r'Общий объем твердотельных накопителей \(SSD\)',
                                     soup)
    ssd_disk_type = find_if_on_page(r'Тип SSD диска', soup)
    notebook["SSD"] = f"{total_ssd_size} {ssd_disk_type}"

    notebook["HDD"] = find_if_on_page(
        r'Общий объем жестких дисков (HDD)',
        soup
    ).capitalize()

    count = 0
    while True:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        if old_price_element := soup.find('span', class_='product-buy__prev'):
            notebook["Цена"], notebook["Цена без скидки"] = map(
                int, soup.find(
                    'div',
                    class_='product-buy__price product-buy__price_active'
                ).text.replace(' ', '').split('₽')
            )
            notebook["Цена без скидки"] = int(old_price_element.text.replace(' ', ''))
            notebook["Скидка"] = round(100 - (
                    notebook["Цена"] / notebook["Цена без скидки"]
            ) * 100)
            break
        elif price := soup.find('div', class_='product-buy__price'):
            notebook["Цена"] = int(price.text.replace(' ', '')[:-1])
            notebook["Цена без скидки"], notebook["Скидка"] = 0, 0
            break
        else:
            count += 1
            pause(1)
    notebook["Ссылка"] = url

    return notebook


def find_if_on_page(regex: str, soup) -> str:
    """
    Проверяет есть ли элемент на странице и, если есть,
    возвращает текст следующего блока div.
    """
    if (element := soup.find(
        text=re.compile(fr"^ ?{regex} ?$"),
    )) is not None:
        return element.find_next("div").text.strip()
    else:
        return "Нет"


def main():
    start_time = time()
    with Chrome(service=Service(ChromeDriverManager().install())) as driver:
        driver.maximize_window()

        print("Получение списка всех ссылок на игровые ноутбуки:")
        urls = get_all_notebook_urls(driver)
        with open('urls.txt', 'w') as file:
            file.write('\n'.join(urls))

        print("Получение характеристик всех игровых ноутбуков:")

        with open('urls.txt', 'r') as file:
            urls = list(map(lambda line: line.strip(), file.readlines()))

        notebooks = []
        for url in tqdm(urls, ncols=70, unit='notebook',
                        colour='green', file=sys.stdout):
            notebooks.append(get_notebook_data(driver, url))

    with open('notebooks_list_pickle.txt', 'wb+') as file:
        pickle.dump(notebooks, file)

    with open('notebooks_list_pickle.txt', 'rb') as file:
        notebooks = pickle.load(file)

    column_names = [
        'Производитель',
        'Модель',
        'Цена',
        'Цена без скидки',
        'Скидка',
        'Процессор',
        'Дискретная видеокарта',
        'Встроенная видеокарта',
        'Оперативная память',
        'SSD',
        'HDD',
        'Экран',
        'Операционная система',
        'Ссылка'
    ]

    to_excel(notebooks, column_names, file_name="notebooks")
    to_json(notebooks, file_name="notebooks")
    to_xml(
        notebooks,
        parameters=column_names,
        root='Ноутбуки',
        item_name='Ноутбук',
        file_name="notebooks"
    )
    to_csv(notebooks, column_names, file_name="notebooks")

    total_time = time() - start_time
    print(f"Время выполнения:\n"
          f"{(total_time // 3600):02.0f}:"
          f"{(total_time % 3600 // 60):02.0f}:"
          f"{(total_time % 60):02.0f}")


if __name__ == '__main__':
    main()
