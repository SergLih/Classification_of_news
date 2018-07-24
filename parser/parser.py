import feedparser
import urllib.request
from bs4 import BeautifulSoup
import datetime
import pandas as pd
from tqdm import tqdm
import re
import time
import socket
from nltk.stem.snowball import SnowballStemmer
from collections import Counter
import numpy as np

NEWS_FILE = 'data.csv.gz'

def source_from_url(url):
    return re.search(r'(?<=:\/\/)([^\:\/\s]+)(?=\/)', url).group(0)


def clean_whitespace(text):
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\t', ' ', text)
    text = re.sub(r'\ {2,}', ' ', text)
    return text

def parse_nplus1(entry):
    url = entry['link']
    if "news" not in url:  # отсеиваем блоги и т.п.
        return
    with urllib.request.urlopen(url) as fp:
        content = fp.read().decode("utf8")
    soup = BeautifulSoup(content, 'html.parser')
    text = ' '.join(p.text for p in soup.select('div.body.js-mediator-article > p'))
    text = text.replace(entry['author'], '').replace('\xa0', ' ').replace('Поделиться', ' ')
    if not text:    
        return
    
    return {'url': url, 'title': entry['title'], 'text': text,
            'dt': pd.Timestamp(entry['published']).tz_convert('Europe/Moscow'),
            'cat': 'nauka', 'source': 'nplus1.ru'}


def parse_tvkultura(entry):
    text = entry['yandex_full-text'].replace('Новости культуры', '')
    if not text:    
        return

    return {'url': entry['link'], 'title': entry['title'], 'text': text,
            'dt': pd.Timestamp(entry['published']).tz_convert('Europe/Moscow'),
            'cat': 'kultura', 'source': 'tvkultura.ru'}


def parse_tass(entry):
    main_cats = ['politika', 'obschestvo', 'mezhdunarodnaya-panorama', 'sport',
                 'ekonomika', 'v-strane', 'proisshestviya', 'kultura', 'nauka']
    url = entry['link']
    cat = url[url.find('.ru/')+4:]
    cat = cat[:cat.find('/')]
    if cat not in main_cats:
        return 
    
    with urllib.request.urlopen(url) as fp:
        content = fp.read().decode("utf8")

    soup = BeautifulSoup(content, 'html.parser')
    text = ' '.join(p.text for p in soup.select('div.b-material-text__l.js-mediator-article > p'))
    if not text:    
        return

    text = text[text.find('.') + 1:]                # Дата, город
    text = re.sub('/[А-Яа-яЁё \.]*/\.', ' ', text)  # / Корр.ТАСС Михаил Тимофеев /.

    return {'url': url, 'title': entry['title'], 'text': text, 
            'dt': pd.Timestamp(entry['published']).tz_convert('Europe/Moscow'), 
            'cat': cat, 'source': 'tass.ru'}


def load_source(dt_last_update, rss_url, parser_func):
    d = feedparser.parse(rss_url)
    news_arr = []
    for entry in tqdm(reversed(d['entries'])):
        dt_object = pd.Timestamp(entry['published']).tz_convert('Europe/Moscow')
        if dt_object <= dt_last_update:  # пропускаем все уже загруженные новости
            continue
        else:
            news_object = parser_func(entry)
            if news_object is not None:
                news_object['text'] = clean_whitespace(news_object['text'])
                news_arr.append(news_object)
                
    return news_arr


def netcat(hostname, port, content):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    s.sendall(content.encode(encoding='utf-8'))
    s.shutdown(socket.SHUT_WR)
    while 1:
        data = s.recv(1024)
        if data != "":
            print(data)
            break
    print("Connection closed.")
    s.close()        

        
def get_stop_words():
    stemmer = SnowballStemmer("russian") 
    with open('./stop-words-russian.txt', encoding='utf-8') as f:
        my_stop_words = f.read().splitlines()
        my_stop_words += ['тасс']
        my_stop_words = set(filter(lambda x: len(x) > 1, (stemmer.stem(w) for w in my_stop_words)))
    return my_stop_words


def update_model(df):
    stemmer = SnowballStemmer("russian") 
    def preprocess_stem(t):
        t = re.sub("[^А-Яа-яЁё]", " ", t.lower())
        return list(filter(lambda x: len(x) > 1, (stemmer.stem(w) for w in t.split())))
        
    cats = df['cat'].unique().tolist()
    with open('./classes.txt', 'w') as f:
        f.write(' '.join(cats))
    
    print('Обновление модели, количество документов: {}, количество категорий: {}'.format(
            df.shape[0], len(cats)))
    
    cat2code = dict(zip(cats, range(len(cats))))
    print(cat2code)
    
    df['stems'] = (df['title'] + df['text']).apply(preprocess_stem)                            # столбец с основами
    y = df['cat'].map(cat2code)                                                                # коды категорий
    
    df_counts = pd.DataFrame(df['stems'].apply(lambda x: dict(Counter(x))).tolist()).fillna(0) # подсчёт встречаемости слов
    print('Общее количество слов:     ', df_counts.shape[1])
    ind = np.where((df_counts > 0).sum(axis=0) >= 2)[0]                  # хотя бы в двух документах
    vocab = sorted(set(df_counts.columns[ind]) - get_stop_words())
    d = df_counts.loc[:, vocab].values
    print('Количество отобранных слов:', len(vocab))

    with open('./words.txt', 'w') as f:
        f.write(' '.join(vocab))

    d = np.log(d + 1)                               # 1. TF-преобразование (частота слова в документах)
    d *= np.log(d.shape[0] / ((d > 0).sum(axis=0))) # 2. IDF преобразование (количество появлений каждого слова в документах)
    d = (d.T / np.sqrt((d**2).sum(axis=1))).T       # 3. Нормализация на длину документов

    psi = np.zeros((len(cats), len(vocab)))         # 4. Мы хотим каждому слову приписать вероятность быть обнаруженным в тексте класса с. 
                                                    #    Делаем это через дополнение по классам -- то есть смотрим на слова в документах остальных классов
    for cat in tqdm(range(len(cats))):
        d_compl = d[np.where(y!=cat)[0], :]
        denom = d_compl.sum() + len(vocab) * 0.1
        psi[cat, :] = (d_compl.sum(axis=0) + 0.1) / denom

    w = np.log(psi)
    w = (w.T / np.abs(w).sum(axis=1)).T

    np.savetxt(fname='./weights.txt', X=w, delimiter=' ')
    print('Новые параметры модели успешно рассчитаны и сохранены')
    
    with open('./classes.txt', 'r') as f:
        classes = f.read()
    with open('./words.txt', 'r') as f:
        words = f.read()
    with open('./weights.txt', 'r') as f:
        weights = f.read()

    netcat('127.0.0.1', 3540, 'UPDATE\n{}\n{}\n{}\n\n'.format(words, classes, weights))
    print('Параметры модели успешно отправлены на сервер')


def main():

    while True:
        try:
            df = pd.read_csv(NEWS_FILE, error_bad_lines=False, parse_dates=['dt'] )
            df['dt'] = df['dt'].dt.tz_localize('UTC').dt.tz_convert('Europe/Moscow')
        except:
            newFile = input("Не могу открыть файл с базой данных новостей. Создать новый? (y/n)")
            if newFile == 'y':
                df = pd.DataFrame()
                
        sources = [('http://tass.ru/rss/v2.xml', parse_tass), 
                   ('https://tvkultura.ru/rss/yandex/', parse_tvkultura),
                   ('https://nplus1.ru/rss', parse_nplus1)]

        for url, parser in sources:
            source = source_from_url(url)
            dt_last_update = df.query('source == @source')['dt'].max()
            print('Источник: {} | Последнее обновление {} | Загрузка новостей...'.format(source, dt_last_update))
            news_arr = load_source(dt_last_update, url, parser)
            if news_arr:
                df = df.append(news_arr, ignore_index=True)
                print('Источник: {} | Добавлено новостей: {}'.format(source, len(news_arr)))
            else:
                print('Источник: {} | Свежих новостей нет'.format(source))

        df.dropna(inplace=True)  # для новостей с непрогрузившимся текстом
        df.to_csv(NEWS_FILE, index=False, compression='gzip')
        update_model(df)
        time.sleep(60*20)
        
if __name__ == '__main__':
    main()
