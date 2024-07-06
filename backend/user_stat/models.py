from django.db import models
from useraccount.models import User
from datetime import date

class UserGoals(models.Choices):
    LoseWeight = "Lose Weight", "Lose Weight"
    MaintainWeight = "Gain Weight", "Maintain Weight"
    GainWeight = "Gain Weight", "Gain Weight"

class UserGender(models.Choices):
    Male = "Male", "Male"
    Female = "Female", "Female"
    Other = "Other", "Other"


class UserMetrics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal = models.CharField(max_length=255, choices=UserGoals.choices, blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=255, choices=UserGender.choices, blank=True, null=True)
    daily_calorie_goal = models.IntegerField(blank=True, null=True)
    daily_protein_goal = models.IntegerField(blank=True, null=True)
    daily_carb_goal = models.IntegerField(blank=True, null=True)
    daily_fat_goal = models.IntegerField(blank=True, null=True)

    @property
    def age(self):
        if self.date_of_birth is None:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    weight = models.FloatField()

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}: {self.weight} kg"