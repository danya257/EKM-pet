# blog/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, DetailView
from .models import Article
from .forms import ArticleForm

def is_editor(user):
    return user.is_staff or user.user_type == 'clinic_admin'

class BlogHomeView(ListView):
    model = Article
    template_name = 'blog/home.html'
    context_object_name = 'articles'
    queryset = Article.objects.filter(is_published=True)

class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

def is_admin(user):
    return user.is_staff

@login_required
@user_passes_test(is_admin)
def article_create_view(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()
            return redirect('blog:home')
    else:
        form = ArticleForm()
    return render(request, 'blog/article_form.html', {'form': form})