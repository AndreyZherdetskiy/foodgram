import re

from rest_framework import serializers

from api.constants import (
    AMOUNT_MIN_VALUE,
    COOKING_TIME_MIN_VALUE,
    PAGINATION_MAX_PAGE_SIZE,
    USERNAME_REGEX
)


def validate_username(value):
    if not re.match(USERNAME_REGEX, value):
        raise serializers.ValidationError(
            'Имя пользователя может содержать только буквы, '
            'цифры и символы . @ + - _'
        )
    return value


def validate_subscription(user, author, recipes_limit):
    from users.models import Subscription

    if user == author:
        raise serializers.ValidationError('Нельзя подписаться на себя.')

    if Subscription.objects.filter(user=user, author=author).exists():
        raise serializers.ValidationError(
            'Вы уже подписаны на этого пользователя.'
        )

    if recipes_limit > PAGINATION_MAX_PAGE_SIZE:
        raise serializers.ValidationError(
            f'Максимальное значение recipes_limit - '
            f'{PAGINATION_MAX_PAGE_SIZE}.'
        )


def validate_cooking_time(value):
    if value < COOKING_TIME_MIN_VALUE:
        raise serializers.ValidationError(
            'Время приготовления должно быть не менее '
            f'{COOKING_TIME_MIN_VALUE} минут(ы).'
        )
    return value


def validate_ingredients(ingredients_data):
    from recipes.models import Ingredient

    if not ingredients_data:
        raise serializers.ValidationError(
            'Необходимо предоставить хотя бы один ингредиент.'
        )

    unique_ids = set()
    ingredient_ids = [ingredient.get('id') for ingredient in ingredients_data]

    existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)

    if len(existing_ingredients) != len(ingredient_ids):
        missing_ids = set(ingredient_ids) - set(
            existing_ingredients.values_list('id', flat=True)
        )
        raise serializers.ValidationError(
            f'Ингредиенты с id {", ".join(map(str, missing_ids))} '
            'не существуют.'
        )

    for ingredient in ingredients_data:
        ingredient_id = ingredient.get('id')

        if ingredient_id in unique_ids:
            raise serializers.ValidationError(
                'Дублирование ингредиентов не допускается.'
            )
        unique_ids.add(ingredient_id)

        if ('amount' not in ingredient
                or ingredient['amount'] < AMOUNT_MIN_VALUE):
            raise serializers.ValidationError(
                'Ингредиент должен иметь положительное количество.'
            )

    return ingredients_data


def validate_tags(tags_data):
    if not tags_data:
        raise serializers.ValidationError(
            'Необходимо предоставить хотя бы один тег.'
        )

    if len(tags_data) != len(set(tags_data)):
        raise serializers.ValidationError(
            'Дублирование тегов не допускается.'
        )

    return tags_data


def validate_image(image):
    if image is None or not image:
        raise serializers.ValidationError(
            'Это поле не может быть пустым.'
        )
    return image
