from django.db import models
from useraccount.models import User
import uuid
from django.utils import timezone



class MealCategory(models.TextChoices):
    BREAKFAST = 'Breakfast', 'Breakfast'
    LUNCH = 'Lunch', 'Lunch'
    DINNER = 'Dinner', 'Dinner'
    SNACK = 'Snack', 'Snack'

class Meal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  
    meal_date = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  
    category = models.CharField(max_length=100, choices=MealCategory.choices)

    def __str__(self):
        return f"{self.category} - {self.meal_date}"
    
class MealItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meal_id = models.ForeignKey(Meal, on_delete=models.CASCADE, null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, null=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(max_length=1000, upload_to='meal_items/', blank=True, null=True)
    carbs = models.PositiveIntegerField(null=True, blank=True)
    proteins = models.PositiveIntegerField(null=True, blank=True)
    fats = models.PositiveIntegerField(null=True, blank=True)
    servings = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name
    

class Prompts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    system_message = models.TextField()
    user_message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  