import feedparser
import urllib.request
from bs4 import BeautifulSoup
import datetime
import pandas as pd
from tqdm import tqdm
import re


d = feedparser.parse('http://tass.ru/rss/v2.xml')
all_news = []

for entry in tqdm(d['entries']):
    # for k, v in entry.items():
    #     print(k, ":", v)
    # break
    url = entry['link']

    with urllib.request.urlopen(url) as fp:
        content = fp.read().decode("utf8")

    soup = BeautifulSoup(content, 'html.parser')
    text = ' '.join(p.text for p in soup.select('div.b-material-text__l.js-mediator-article > p'))
    if not text:    # дизайн ЧМ-2018
        text = ' '.join(p.text for p in soup.select('div.article__text > p'))
    if not text:    # если текст лежит ни в одном из двух дизайнов, то переходим к следующей новости
        continue

    text = text[text.find('.') + 1:]
    text = re.sub('/[А-Яа-я \.]*/\.', ' ', text)  # / Корр.ТАСС Михаил Тимофеев /.

    dt_object = datetime.datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %z')
    cat = url[url.find('.ru/')+4:]
    cat = cat[:cat.find('/')]

    news = {'url': url, 'title': entry['title'], 'dt': dt_object, 'text': text, 'cat': cat}
    all_news.append(news)


df = pd.DataFrame(all_news)
df.to_csv('./data.csv', mode='a', header=False)
