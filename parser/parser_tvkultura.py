import feedparser
import urllib.request
from bs4 import BeautifulSoup
import datetime
import pandas as pd
from tqdm import tqdm


d = feedparser.parse('https://tvkultura.ru/rss/yandex/')
all_news = []

for entry in tqdm(d['entries']):
    # for k, v in entry.items():
    #     print(k, ":", v)
    # break
    url = entry['link']

    text = entry['yandex_full-text']
    text = text.replace('Новости культуры', '')

    dt_object = datetime.datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %Z')
    cat = 'kultura'

    news = {'url': url, 'title': entry['title'], 'dt': dt_object, 'text': text, 'cat': cat}
    all_news.append(news)

# print(all_news)
df = pd.DataFrame(all_news)
df.to_csv('./data.csv', mode='a', header=False)
