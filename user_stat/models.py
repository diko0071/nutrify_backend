from django.db import models
from useraccount.models import User
from datetime import date

class UserGoals(models.TextChoices):
    LoseWeight = "Lose Weight", "Lose Weight"
    MaintainWeight = "Maintain Weight", "Maintain Weight"
    GainWeight = "Gain Weight", "Gain Weight"

class UserGender(models.TextChoices):
    Male = "Male", "Male"
    Female = "Female", "Female"

class UserActivityLevel(models.TextChoices):
    Sedentary = "Sedentary", "Sedentary"
    LightlyActive = "Lightly Active", "Lightly Active"
    ModeratelyActive = "Moderately Active", "Moderately Active"
    VeryActive = "Very Active", "Very Active"
    ExtraActive = "Extra Active", "Extra Active"

class UserMetrics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    goal = models.CharField(max_length=255, choices=UserGoals.choices, blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=255, choices=UserGender.choices, blank=True, null=True)
    activity_level = models.CharField(max_length=255, choices=UserActivityLevel.choices, blank=True, null=True)
    daily_calorie_goal = models.IntegerField(blank=True, null=True)
    daily_protein_goal = models.IntegerField(blank=True, null=True)
    daily_carb_goal = models.IntegerField(blank=True, null=True)
    daily_fat_goal = models.IntegerField(blank=True, null=True)


    def calculate_age(self):
        if self.date_of_birth is None:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def calculate_bmr(self):
        if self.age is None or self.weight is None or self.height is None:
            return None
        
        if self.gender == UserGender.Male:
            bmr = 66.47 + (13.75 * self.weight) + (5.003 * self.height) - (6.755 * self.age)
        
        elif self.gender == UserGender.Female:
            bmr = 655.1 + (9.563 * self.weight) + (1.85 * self.height) - (4.676 * self.age)
        
        return bmr

    def calculate_daily_calorie_goal(self):
        bmr = self.calculate_bmr()
        if bmr is None:
            return None

        activity_multiplier = {
            UserActivityLevel.Sedentary: 1.2,
            UserActivityLevel.LightlyActive: 1.375,
            UserActivityLevel.ModeratelyActive: 1.55,
            UserActivityLevel.VeryActive: 1.725,
            UserActivityLevel.ExtraActive: 1.9
        }.get(self.activity_level, 1.2)

        return bmr * activity_multiplier

    def calculate_macronutrient_goals(self):
        if self.daily_calorie_goal is None:
            return None

        self.daily_protein_goal = int(self.daily_calorie_goal * 0.20 / 4)
        self.daily_carb_goal = int(self.daily_calorie_goal * 0.50 / 4)
        self.daily_fat_goal = int(self.daily_calorie_goal * 0.30 / 9)

    def save(self, *args, **kwargs):
        self.age = self.calculate_age()
        self.daily_calorie_goal = self.calculate_daily_calorie_goal()
        self.calculate_macronutrient_goals()
        super().save(*args, **kwargs)


class WeightLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    weight = models.FloatField()

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}: {self.weight} kg"