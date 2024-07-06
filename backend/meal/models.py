from django.db import models
from useraccount.models import User
import uuid

class MealItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    calories = models.PositiveIntegerField()
    image = models.ImageField(upload_to='meal_items/', blank=True, null=True)
    carbs = models.PositiveIntegerField()
    proteins = models.PositiveIntegerField()
    fats = models.PositiveIntegerField()

    def __str__(self):
        return self.name

class Meal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
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