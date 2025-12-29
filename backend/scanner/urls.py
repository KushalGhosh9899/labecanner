from django.urls import path
from .views import analyze_label_api

urlpatterns = [
    path('api/analyze/', analyze_label_api, name='analyze_label_api'),
]