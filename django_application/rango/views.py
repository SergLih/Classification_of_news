import socket
import re
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
# Import the Category model
from rango.models import *
from rango.forms import *
from django.conf import settings
from django.db import IntegrityError
from nltk.stem.snowball import SnowballStemmer
from django.urls import reverse

stemmer = SnowballStemmer("russian") 

def show_category(request, category_name_slug):
    # Create a context dictionary which we can pass
    # to the template rendering engine.
    context_dict = {}

    try:
        # Can we find a category name slug with the given name?
        # If we can't, the .get() method raises a DoesNotExist exception.
        # So the .get() method returns one model instance or raises an exception.
        category = Category.objects.get(slug=category_name_slug)

        # Retrieve all of the associated pages.
        # Note that filter() will return a list of page objects or an empty list
        articles = Article.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['articles'] = articles
        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category'] = category

    except Category.DoesNotExist:
        # We get here if we didn't find the specified category.
        # Don't do anything -
        # the template will display the "no category" message for us.
        context_dict['category'] = None
        context_dict['articles'] = None
    # Go render the response and return it to the client.
    return render(request, 'rango/category.html', context_dict)

def index(request):
    # Query the database for a list of ALL categories currently stored.
    # Order the categories by no. likes in descending order.
    # Retrieve the top 5 only - or all if less than 5.
    # Place the list in our context_dict dictionary
    # that will be passed to the template engine.
    new_articles = Article.objects.all().order_by('-published')[:10]
    context_dict = {'new_articles': new_articles}
    # Render the response and send it back!
    return render(request, 'rango/index.html', context_dict)
    

  
def add_category(request):
    form = CategoryForm()

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        
        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)
            # Now that the category is saved
            # We could give a confirmation message
            # But since the most recent category added is on the index page
            # Then we can direct the user back to the index page.
            return index(request)
        else:
            # The supplied form contained errors -
            # just print them to the terminal.
            print(form.errors)

    # Will handle the bad form, new form, or no form supplied cases.
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})

def add_article(request):
    def preprocess_stem(t):
        t = re.sub("[^А-Яа-яЁё]", " ", t.lower())
        t = t.replace('ё', 'е').replace('Ё', 'Е')
        return ' '.join(filter(lambda x: len(x) > 1, (stemmer.stem(w) for w in t.split())))

    def netcat(hostname, port, content):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((hostname, port))
        s.sendall(content.encode(encoding='utf-8'))
        s.shutdown(socket.SHUT_WR)
        while 1:
            data = s.recv(1024)
            if data != "":
                s.close()
                return data

    form = ArticleForm()
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            stems = preprocess_stem(page.title + ' ' + page.text)
            
            try:
                response = netcat(settings.GODAEMON_ADDRESS, settings.GODAEMON_PORT, 
                                'CLASSIFY\n{}\n'.format(stems)).decode('utf-8').splitlines()
                status, cat = response[:2]
                
            except ConnectionRefusedError:
                status, cat = 'ERROR', 'Нет соединения с сервером'


            if status == 'OK':
                try:
                    cat = Category.objects.get(slug=cat)
                    page.category = cat
                    page.save()
                    return redirect(reverse('show_article', kwargs={'category_slug':cat.slug, 'article_slug': page.slug}))
                except Category.DoesNotExist:
                    status = 'ERROR'
                    cat = 'Сервер вернул категорию, которой нет в базе'
        else:
            print(form.errors)
    else:
        status, cat = 'OK', None
    context_dict = {'form':form, 'status': status, 'category': cat}
    return render(request, 'rango/add_article.html', context_dict)

def show_article(request, category_slug, article_slug):
        
    print('*************', category_slug, article_slug)
        
    context_dict = {}

    try:
        category = Category.objects.get(slug=category_slug)

        extra_articles = Article.objects.filter(category=category).order_by('-published')[:5]
        
        article = Article.objects.get(slug=article_slug)

        context_dict['extra_articles'] = extra_articles
        context_dict['category'] = category
        context_dict['article'] = article
        

    except Category.DoesNotExist:
        raise Http404("Указанная категория новостей не найдена")
        
    except Article.DoesNotExist:
        raise Http404("Указанная новость не найдена")
    
    # Go render the response and return it to the client.
    return render(request, 'rango/article.html', context_dict)
    
    
def about(request):
    return HttpResponse("Rango says: \"ЛОЛ КЕК ЧЭБУРЭК\" <a href=\"/\">главная</>")

