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
from .services import MealItemHandler, AdvancedMealItemHandler
import json
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

@api_view(['GET'])
def get_recipe(request):
    user = request.user
    model = AdvancedMealItemHandler(user)
    data = request.data.get('data')
    date = request.data.get('date')
    date = datetime.strptime(date, '%Y-%m-%d')
    input_type = 'description'
    meal_category = request.data.get('meal_category')

    try:
        meal = Meal.objects.filter(category=meal_category, user=user, meal_date=date).latest('meal_date')
    except Meal.DoesNotExist:
        meal = Meal.objects.create(category=meal_category, user=user, meal_date=date)
    
    if 'image' in request.data:
       input_type = 'image'
       image = request.FILES.get('image')
       image = default_storage.save(image.name, ContentFile(image.read()))
       image_url = default_storage.url(image)
       recipe = model.calculate_calories_by_meal_name(image_url, input_type, meal, image)
       serialized_meal_item = MealItemSerializer(recipe, many=True)
       return Response(serialized_meal_item.data)
    else:
        recipe = model.calculate_calories_by_meal_name(data, input_type, meal)
        serialized_meal_item = MealItemSerializer(recipe, many=True)
        return Response(serialized_meal_item.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_meal_items(request):
    meal_items = MealItem.objects.all()
    serializer = MealItemSerializer(meal_items, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_meal_items_for_meal(request):
    user = request.user
    meal_id = request.data.get('meal_id')
    meal_items = MealItem.objects.filter(meal_id=meal_id, user=user)
    serializer = MealItemSerializer(meal_items, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def create_meal_item(request):
    user = request.user
    date = request.data.get('date')
    date = datetime.strptime(date, '%Y-%m-%d')
    model = MealItemHandler(user)
    meal_category = request.data.get('meal_category')

    try:
        meal = Meal.objects.filter(category=meal_category, user=user, meal_date=date).latest('meal_date')
    except Meal.DoesNotExist:
        meal = Meal.objects.create(category=meal_category, user=user, meal_date=date)

    description = request.data.get('description')
    image = request.FILES.get('image')

    try:
        if image and not description:
            image = default_storage.save(image.name, ContentFile(image.read()))
            image_url = default_storage.url(image)
            meal_item = model.generate_meal_item_by_picture(image_url, image, meal)
            serialized_meal_item = MealItemSerializer(meal_item, many=True)
            return Response(serialized_meal_item.data)
    
    except Exception as e:
        return Response({"error": str(e)})

    try:
        if description and not image:
            meal_item = model.generate_meal_item_by_description(description, meal)
            serialized_meal_item = MealItemSerializer(meal_item, many=True)
            return Response(serialized_meal_item.data)

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

