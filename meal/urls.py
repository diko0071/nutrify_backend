from django.urls import path
from .views import *

urlpatterns = [
    path('get_meal_items_for_meal/', get_meal_items_for_meal, name='get_meal_items_for_meal'),
    path('create_meal_item/', create_meal_item, name='create_meal_item'),
    path('update_meal_item/<int:meal_item_id>/', update_meal_item, name='update_meal_item'),
    path('delete_meal_item/<int:meal_item_id>/', delete_meal_item, name='delete_meal_item'),
    path('get_all_meal_items/', get_all_meal_items, name='get_all_meal_items'),
    path('get_recipe/', get_recipe, name='get_recipe'),
] 