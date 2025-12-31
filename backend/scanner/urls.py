from django.urls import path
from .views import analyze_label_api, analyze_ingredients_api, scanner_pipeline_api
from django.views.generic import TemplateView

urlpatterns = [
    path('api/analyze/', analyze_label_api, name='analyze'),
    path('api/extract/', analyze_ingredients_api, name = 'extract'),
    path('api/run-piepline/', scanner_pipeline_api, name='extract-pipeline'),
    path('scanner-ui/', TemplateView.as_view(template_name='scanner/scanner_home.html'), name='scanner_ui'),
]