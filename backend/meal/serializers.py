from rest_framework import serializers
from .models import MealItem

class MealItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealItem
        fields = '__all__'