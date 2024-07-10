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
from .services import MealItemHandler
import json
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from azure.storage.blob import BlobServiceClient



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

@api_view(['POST'])
def create_meal_item_ai(request):
    user = request.user
    model = MealItemHandler(user)
    
    meal_id = request.data.get('meal_id')
    description = request.data.get('description')
    picture = request.FILES.get('picture')

    try:
        if picture and not description:
            image = default_storage.save(picture.name, ContentFile(picture.read()))
            image_url = default_storage.url(image)
            meal_item = model.generate_meal_item_by_picture(image_url, image, meal_id)
            serialized_meal_item = MealItemSerializer(meal_item)
            return Response(serialized_meal_item.data)
    
    except Exception as e:
        return Response({"error": str(e)})

    try:
        if description and not picture:
            meal_item = model.generate_meal_item_by_description(description, meal_id)
            return Response(meal_item)

    except Exception as e:
        return Response({"error": str(e)})

    return Response({"error": "Both picture and description cannot be provided or both are missing"}, status=400)

@api_view(['PUT'])
def update_meal_item(request, meal_item_id):
    user = request.user
    try:
        meal_item = MealItem.objects.get(id=meal_item_id, user=user)
    except MealItem.DoesNotExist:
        return Response({"error": "Meal item not found"}, status=404)

    serializer = MealItemSerializer(meal_item, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)

@api_view(['DELETE'])
def delete_meal_item(request, meal_item_id):
    user = request.user
    try:
        meal_item = MealItem.objects.get(id=meal_item_id, user=user)
    except MealItem.DoesNotExist:
        return Response({"error": "Meal item not found"}, status=404)

    meal_item.delete()
    return Response({"message": "Meal item deleted successfully"}, status=204)

