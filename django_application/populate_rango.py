import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'tango_with_django_project.settings')
                      
import pandas as pd
from tqdm import tqdm
import django
django.setup()

from rango.models import Category, Page

def populate():
 # First, we will create lists of dictionaries containing the pages
 # we want to add into each category.
 # Then we will create a dictionary of dictionaries for our categories.
 # This might seem a little bit confusing, but it allows us to iterate
 # through each data structure, and add the data to our models.

    main_cats = {'politika': 'Политика', 'obschestvo': 'Общество', 'mezhdunarodnaya-panorama': 'Международная политика', 'sport': 'Спорт', 'ekonomika': 'Экономика', 'v-strane': 'В стране', 'proisshestviya': 'Происшествия', 'kultura': 'Культура', 'nauka': 'Наука'}

    for slug, name in main_cats.items():
        c_obj = Category.objects.get_or_create(name=name, slug=slug)[0]
        c_obj.save()

 # Start execution here!
if __name__ == '__main__':
    print("Starting Rango population script...")
    populate()
