from django.shortcuts import render
from rest_framework.response import Response
import requests
import os 
from dotenv import load_dotenv
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from .serializers import MealItemSerializer, MealSerializer
from .models import MealItem, Meal
from datetime import datetime, timedelta
import json



# Get meal items for a meal and all meals for day
@api_view(['GET'])
def get_meal_items_for_meal(request, meal_id):
    user = request.user
    meal_items = MealItem.objects.filter(meal_id=meal_id, user=user)
    serializer = MealItemSerializer(meal_items, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_meal_by_day(request):
    user = request.user
    day = request.query_params.get('day')
    meal = Meal.objects.get(day=day, user=user)
    serializer = MealSerializer(meal)
    return Response(serializer.data)

# Interact with meal items
@api_view(['POST'])
def create_meal_item(request):
    ...

@api_view(['POST'])
def create_meal_item_ai(request):
    ...

@api_view(['PUT'])
def update_meal_item(request):
    ...

@api_view(['DELETE'])
def delete_meal_item(request):
    ...


