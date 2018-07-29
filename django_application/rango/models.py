from django.db import models
import re
import unidecode


def slugify(str):
    return re.sub(r'[^\w]+', '-', unidecode.unidecode(str).lower().strip()).strip('-')


class Category(models.Model):
    max_name_length = 128

    name = models.CharField(max_length=max_name_length, unique=True)
    slug  = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self): # For Python 2, use __unicode__ too
        return self.name


class Page(models.Model):
    category  = models.ForeignKey(Category)
    title     = models.CharField(max_length=255)
    text      = models.TextField(null=True)
    url       = models.URLField()
    published = models.DateTimeField(null=True)
    views     = models.IntegerField(default=0)

    def __str__(self):
        return self.title


class Article(models.Model):
    category  = models.ForeignKey(Category)
    title     = models.CharField(max_length=255)
    text      = models.TextField(null=True)
    url       = models.URLField()
    published = models.DateTimeField(auto_now_add=True)
    slug      = models.SlugField(unique=True)
    
    def __str__(self):
        return self.title
      
        
    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        similar_slugs = Article.objects.filter(slug__startswith=self.slug)
        if len(similar_slugs) > 0:
            self.slug += '-' + str(len(similar_slugs) + 1)
        super(Article, self).save(*args, **kwargs)   
