from django import forms
from rango.models import Page, Category, Article

class CategoryForm(forms.ModelForm):
    name  = forms.CharField(max_length=Category.max_name_length, help_text="Please enter the category name.")
    views = forms.IntegerField(widget=forms.HiddenInput(), initial=0)
    likes = forms.IntegerField(widget=forms.HiddenInput(), initial=0)
    slug  = forms.CharField(widget=forms.HiddenInput(), required=False)

    # An inline class to provide additional information on the form.
    class Meta:
        # Provide an association between the ModelForm and a model
        model = Category
        fields = ('name',)


class ArticleForm(forms.ModelForm):
    title     = forms.CharField(max_length=128,
                                help_text="Введите заголовок.")
    text      = forms.CharField(help_text="Введите текст новости.", widget=forms.Textarea)
    url       = forms.URLField( max_length=200,
                                help_text="Введите ссылку на источник новости.")
    slug      = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Article
        exclude = ('category','published', 'slug')


class PageForm(forms.ModelForm):
    title = forms.CharField(max_length=128,
                            help_text="Please enter the title of the page.")
    url = forms.URLField(max_length=200,
                         help_text="Please enter the URL of the page.")
    views = forms.IntegerField(widget=forms.HiddenInput(), initial=0)

    class Meta:
        model = Page

        exclude = ('category',)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        url = cleaned_data.get('url')

        if url and not url.startswith('http://'):
            url = 'http://' + url
            cleaned_data['url'] = url

            return cleaned_data
