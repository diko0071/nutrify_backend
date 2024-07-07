from django.db import models
from useraccount.models import User
import uuid
from django.utils import timezone



class MealCategory(models.TextChoices):
    BREAKFAST = 'Breakfast', 'Breakfast'
    LUNCH = 'Lunch', 'Lunch'
    DINNER = 'Dinner', 'Dinner'
    SNACK = 'Snack', 'Snack'

class MealItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    calories = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='meal_items/', blank=True, null=True)
    carbs = models.PositiveIntegerField(null=True, blank=True)
    proteins = models.PositiveIntegerField(null=True, blank=True)
    fats = models.PositiveIntegerField(null=True, blank=True)
    servings = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

class Meal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, choices=MealCategory.choices)
    meals = models.ManyToManyField(MealItem, related_name='meals')

    def _sum_meal_attribute(self, attribute):
        return sum(getattr(meal, attribute) for meal in self.meals.all())

    @property
    def total_calories(self):
        return self._sum_meal_attribute('calories')

    @property
    def total_carbs(self):
        return self._sum_meal_attribute('carbs')

    @property
    def total_proteins(self):
        return self._sum_meal_attribute('proteins')

    @property
    def total_fats(self):
        return self._sum_meal_attribute('fats')

    def __str__(self):
        return self.name
    

class Prompts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    system_message = models.TextField()
    user_message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)  