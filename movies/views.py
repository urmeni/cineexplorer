from django.shortcuts import render
from django.core.paginator import Paginator
from .services import mongo_service
import math
import json

def home(request):
    stats = mongo_service.get_home_stats()
    top_movies = mongo_service.get_top_rated_movies()
    recent_movies = mongo_service.get_recent_movies()

    return render(request, 'movies/home.html', {
        'stats': stats,
        'top_movies': top_movies,
        'recent_movies': recent_movies
    })


def movie_list(request):
    # Récupération des paramètres GET
    page = int(request.GET.get('page', 1))
    genre = request.GET.get('genre')
    year_min = request.GET.get('year_min')
    rating_min = request.GET.get('rating_min')
    sort_by = request.GET.get('sort', 'year_desc')

    filters = {
        "genre": genre,
        "year_min": year_min,
        "rating_min": rating_min
    }

    # Appel MongoDB
    movies, total_count = mongo_service.search_movies(page=page, filters=filters, sort_by=sort_by)
    genres = mongo_service.get_all_genres()

    # Calcul pagination manuel (car pas de QuerySet Django)
    total_pages = math.ceil(total_count / 20)
    page_range = range(max(1, page - 2), min(total_pages, page + 2) + 1)

    return render(request, 'movies/list.html', {
        'movies': movies,
        'genres': genres,
        'current_page': page,
        'total_pages': total_pages,
        'page_range': page_range,
        'total_count': total_count,
        # On renvoie les filtres pour garder le formulaire rempli
        'selected_genre': genre,
        'selected_year': year_min,
        'selected_rating': rating_min,
        'selected_sort': sort_by
    })


def movie_detail(request, mid):
    movie = mongo_service.get_movie_detail(mid)
    similar = mongo_service.get_similar_movies(movie)
    return render(request, 'movies/detail.html', {'movie': movie, 'similar': similar})


def search(request):
    query = request.GET.get('q', '')
    results = mongo_service.global_search(query) if query else None
    return render(request, 'movies/search.html', {'query': query, 'results': results})


def search(request):
    query = request.GET.get('q', '')
    results = mongo_service.global_search(query) if query else None
    return render(request, 'movies/search.html', {'query': query, 'results': results})


def stats_view(request):
    # Récupération des données brutes
    raw_genres = mongo_service.get_stats_genres()
    raw_decades = mongo_service.get_stats_decades()
    raw_ratings = mongo_service.get_stats_ratings()

    # Préparation pour Chart.js (Listes JSON)
    context = {
        'genres_labels': json.dumps([d['_id'] for d in raw_genres]),
        'genres_data': json.dumps([d['count'] for d in raw_genres]),

        'decades_labels': json.dumps([str(d['_id']) for d in raw_decades]),
        'decades_data': json.dumps([d['count'] for d in raw_decades]),

        'ratings_labels': json.dumps([str(d['_id']) for d in raw_ratings]),
        'ratings_data': json.dumps([d['count'] for d in raw_ratings]),

        'total_movies': mongo_service.get_home_stats()['movies']
    }
    return render(request, 'movies/stats.html', context)