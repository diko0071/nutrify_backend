from django.urls import path
from .views import *

urlpatterns = [
    path('get_all_meal_items/', get_all_meal_items, name='get_all_meal_items'),
]