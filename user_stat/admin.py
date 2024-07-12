from django.contrib import admin
from .models import UserMetrics, WeightLog

admin.site.register(UserMetrics)
admin.site.register(WeightLog)
