from django.conf.urls import url
from rango import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^add_article/$', views.add_article, name='add_article'),
    url(r'^(?P<category_slug>[\w\-]+)/(?P<article_slug>[\w\-]+)/$', views.show_article, name='show_article'),
    url(r'^(?P<category_name_slug>[\w\-]+)/$', views.show_category, name='show_category'),
]
