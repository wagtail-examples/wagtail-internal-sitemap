from django.urls import path

from model_inspector.api_views import APIIndexView

urlpatterns = [
    path("", APIIndexView.as_view(), name="api-view"),
]
