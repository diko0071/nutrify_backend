from django.urls import path
from .views import *

urlpatterns = [
    path("create_collection/", create_collection, name="create_collection"),
    path("add_to_collection/", add_to_collection, name="add_to_collection"),
    path("search_similar_vectors/", search_similar_vectors, name="search_similar_vectors"),
]