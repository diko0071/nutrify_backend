from rest_framework import serializers
from .models import MealItem, Meal
from useraccount.models import User

class MealItemSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = MealItem
        fields = '__all__'


class MealSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    class Meta:
        model = Meal
        fields = '__all__'