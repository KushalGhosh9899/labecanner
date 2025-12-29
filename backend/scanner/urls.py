from django.urls import path
from .views import analyze_label_api, analyze_ingredients_api

urlpatterns = [
    path('api/analyze/', analyze_label_api, name='analyze'),
    path('api/extract/', analyze_ingredients_api, name = 'extract')
]