from django.urls import path
from .views import *

urlpatterns = [
    path("create_collection/", create_collection, name="create_collection"),
]