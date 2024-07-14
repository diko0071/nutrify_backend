from django.shortcuts import render
from rest_framework.response import Response
import requests
import os 
from dotenv import load_dotenv
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from .services import VectorStoreActions

actions = VectorStoreActions()

@api_view(['POST'])
@permission_classes([AllowAny])
def create_collection(request):
    collection_name = request.data.get('collection_name')
    size = 1536
    collection = actions.create_collection(collection_name, size)
    return Response(collection)

@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_collection(request):
    text = request.data.get('text')
    collection_name = request.data.get('collection_name')
    vector = actions.generate_vector(text)
    print(vector)
    payload = {"source": "test", "text": text}
    added = actions.add_vector_to_collection(collection_name, vector, payload)
    print(added)
    return Response({"message": "Vector added to collection"})


@api_view(['POST'])
@permission_classes([AllowAny])
def search_similar_vectors(request):
    collection_name = request.data.get('collection_name')
    text = request.data.get('text')
    search_results = actions.run_search_query_with_text(collection_name, text, limit=1)
    return Response(search_results)
