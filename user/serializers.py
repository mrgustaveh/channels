from rest_framework.serializers import ModelSerializer
from .models import Account


class AccountSerializer(ModelSerializer):
    class Meta:
        model = Account
        fields = ['account_id', 'username', 'display_pic', 'created']