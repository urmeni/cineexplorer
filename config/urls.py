from django.contrib import admin
from django.urls import path
from movies import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('movies/', views.movie_list, name='movie_list'),
    path('movies/<str:mid>/', views.movie_detail, name='movie_detail'),
    path('search/', views.search, name='search'),
    path('stats/', views.stats_view, name='stats'), # Nouvelle vue graphique
]