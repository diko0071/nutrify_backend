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
    size = request.data.get('size')
    collection = actions.create_collection(collection_name, size)
    return Response(collection)