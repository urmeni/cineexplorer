from django.shortcuts import render
from .services import sqlite_service, mongo_service


def test_stats_view(request):
    # Appel des services
    sql_data = sqlite_service.get_sqlite_stats()
    mongo_data = mongo_service.get_mongo_stats()

    context = {
        'sqlite': sql_data,
        'mongo': mongo_data
    }
    return render(request, 'stats.html', context)