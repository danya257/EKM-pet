# blog/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

class Article(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Ссылка', unique=True)
    content = models.TextField('Содержание')
    published_at = models.DateTimeField('Опубликовано', auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_published = models.BooleanField('Опубликовано', default=True)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:article_detail', kwargs={'slug': self.slug})