from django.urls import path
from . import views

urlpatterns = [
    path('', views.live_matches, name='live_matches'),
]