# Generated by Django 5.0.2 on 2024-07-10 02:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("meal", "0003_meal_total_calories_meal_total_carbs_meal_total_fats_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mealitem",
            name="name",
            field=models.CharField(max_length=500),
        ),
    ]
