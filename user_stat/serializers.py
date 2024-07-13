from rest_framework import serializers
from user_stat.models import UserMetrics


class UserStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMetrics
        fields = '__all__'