from django.shortcuts import render
from rest_framework.response import Response
import requests
import os 
from dotenv import load_dotenv
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from .serializers import MealItemSerializer
from .models import MealItem
from datetime import datetime, timedelta
import json



@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_meal_items(request):
    meal_items = MealItem.objects.all()
    serializer = MealItemSerializer(meal_items, many=True)
    return Response(serializer.data)