import re

from rest_framework import serializers

from api.constants import USERNAME_REGEX


def validate_username(value):
    if not re.match(USERNAME_REGEX, value):
        raise serializers.ValidationError(
            'Имя пользователя может содержать только буквы, '
            'цифры и символы . @ + - _'
        )
    return value
