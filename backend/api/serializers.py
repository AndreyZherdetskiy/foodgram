import base64
import re

from django.contrib.auth import password_validation
from django.core.files.base import ContentFile
from rest_framework import serializers

from api.constants import (AMOUNT_MIN_VALUE,
                           COOKING_TIME_MIN_VALUE,
                           PAGINATION_MAX_PAGE_SIZE,
                           RECIPES_LIMIT_DEFAULT,
                           RECIPES_LIMIT_MIN_VALUE)
from recipes.models import (Favorite,
                            Ingredient,
                            Recipe,
                            RecipeIngredient,
                            ShoppingCart,
                            Tag)
from users.models import CustomUser, Subscription


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                format, imgstr = data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(
                    base64.b64decode(imgstr),
                    name=f'temp.{ext}'
                )
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    'Неверный формат изображения.'
                )
        return super().to_internal_value(data)


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        read_only_fields = ('id',)

    def validate_username(self, value):
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError(
                'Имя пользователя может содержать только буквы, '
                'цифры и символы . @ + - _'
            )
        return value

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    def to_representation(self, instance):
        return {
            'email': instance.email,
            'id': instance.id,
            'username': instance.username,
            'first_name': instance.first_name,
            'last_name': instance.last_name,
        }


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField('get_is_subscribed')
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )
        extra_kwargs = (
            {'avatar': {'required': False}}
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False


class SubscriptionSerializer(serializers.ModelSerializer):
    recipes_limit = serializers.IntegerField(
        min_value=RECIPES_LIMIT_MIN_VALUE,
        default=RECIPES_LIMIT_DEFAULT,
        write_only=True
    )

    class Meta:
        model = Subscription
        fields = ('user', 'author', 'recipes_limit')

    def validate(self, data):
        user = data['user']
        author = data['author']
        recipes_limit = data.get('recipes_limit', RECIPES_LIMIT_DEFAULT)

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

        return data

    def create(self, validated_data):
        user = validated_data['user']
        author = validated_data['author']

        subscription = Subscription.objects.create(
            user=user,
            author=author
        )

        return subscription

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj.author
            ).exists()
        return False

    def to_representation(self, instance):
        recipes_limit = self.context.get('recipes_limit')
        if recipes_limit is not None:
            try:
                recipes_limit = int(recipes_limit)
            except ValueError:
                recipes_limit = RECIPES_LIMIT_DEFAULT

        representation = {
            'id': instance.author.id,
            'username': instance.author.username,
            'first_name': instance.author.first_name,
            'last_name': instance.author.last_name,
            'email': instance.author.email,
            'is_subscribed': self.get_is_subscribed(instance),
            'avatar': (
                instance.author.avatar.url if instance.author.avatar else None
            ),
            'recipes_count': instance.author.recipes.count(),
            'recipes': [
                {
                    'id': recipe.id,
                    'name': recipe.name,
                    'image': recipe.image.url if recipe.image else None,
                    'cooking_time': recipe.cooking_time
                }
                for recipe in instance.author.recipes.all()[:recipes_limit]
            ]
        }

        return representation


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_current_password(self, data):
        if not self.context['request'].user.check_password(data):
            raise serializers.ValidationError('Неправильный текущий пароль.')
        return data

    def validate_new_password(self, data):
        password_validation.validate_password(
            password=data,
            user=self.context['request'].user
        )
        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id',)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        read_only_fields = ('id',)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ('ingredient', 'amount')

    def to_representation(self, instance):
        return {
            'id': instance.ingredient.id,
            'name': instance.ingredient.name,
            'measurement_unit': instance.ingredient.measurement_unit,
            'amount': instance.amount
        }


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipeingredient_set'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.in_cart_by.filter(user=request.user).exists()
        return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = instance.id
        representation['is_favorited'] = self.get_is_favorited(instance)
        representation['is_in_shopping_cart'] = (
            self.get_is_in_shopping_cart(
                instance
            )
        )
        representation['tags'] = TagSerializer(
            instance.tags.all(),
            many=True
        ).data
        representation['ingredients'] = [
            {
                'id': ri.ingredient.id,
                'name': ri.ingredient.name,
                'measurement_unit': ri.ingredient.measurement_unit,
                'amount': ri.amount,
            }
            for ri in instance.recipeingredient_set.all()
        ]
        representation['name'] = instance.name
        representation['image'] = (
            instance.image.url if instance.image else None
        )
        representation['text'] = instance.text
        representation['cooking_time'] = instance.cooking_time

        return representation


class IngredientIdAmountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=AMOUNT_MIN_VALUE)


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientIdAmountSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True
    )
    image = Base64ImageField(write_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.in_cart_by.filter(user=request.user).exists()
        return False

    def validate_cooking_time(self, value):
        if value < COOKING_TIME_MIN_VALUE:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее '
                f'{COOKING_TIME_MIN_VALUE} минут(ы).'
            )
        return value

    def validate_tags(self, tags):
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Дублирование тегов не допускается.'
            )
        return tags

    def validate_ingredients(self, ingredients):
        unic_ids = set()
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            if ingredient_id in unic_ids:
                raise serializers.ValidationError(
                    f'Дублирование ингредиента с id '
                    f'{ingredient_id} не допускается.'
                )
            unic_ids.add(ingredient_id)
        return ingredients

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])

        if not ingredients_data:
            raise serializers.ValidationError(
                'Необходимо предоставить хотя бы один ингредиент.'
            )
        if not tags_data:
            raise serializers.ValidationError(
                'Необходимо предоставить хотя бы один тег.'
            )

        ingredient_ids = [
            ingredient.get('id') for ingredient in ingredients_data
        ]
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)

        if len(existing_ingredients) != len(ingredient_ids):
            missing_ids = set(ingredient_ids) - set(
                existing_ingredients.values_list('id', flat=True)
            )
            raise serializers.ValidationError(
                f'Ингредиенты с id {", ".join(map(str, missing_ids))} '
                'не существуют.'
            )

        request = self.context.get('request')
        validated_data['author'] = request.user

        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            if ingredient_id is None or amount is None or amount <= 0:
                continue
            ingredient = existing_ingredients.get(id=ingredient_id)
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            )

        recipe.tags.set(tags_data)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])

        if not ingredients_data:
            raise serializers.ValidationError(
                'Необходимо предоставить хотя бы один ингредиент.'
            )
        if not tags_data:
            raise serializers.ValidationError(
                'Необходимо предоставить хотя бы один тег.'
            )

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time',
            instance.cooking_time
        )
        instance.save()

        instance.ingredients.clear()

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            if ingredient_id is None or amount is None or amount <= 0:
                continue
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient,
                    amount=amount
                )
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f'Ингредиент с id {ingredient_id} не существует.'
                )

        instance.tags.set(tags_data)

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['id'] = instance.id
        representation['is_favorited'] = self.get_is_favorited(instance)
        representation['is_in_shopping_cart'] = (
            self.get_is_in_shopping_cart(
                instance
            )
        )
        representation['tags'] = TagSerializer(
            instance.tags.all(),
            many=True
        ).data
        representation['ingredients'] = [
            {
                'id': ri.ingredient.id,
                'name': ri.ingredient.name,
                'measurement_unit': ri.ingredient.measurement_unit,
                'amount': ri.amount,
            }
            for ri in instance.recipeingredient_set.all()
        ]
        representation['name'] = instance.name
        representation['image'] = (
            instance.image.url if instance.image else None
        )
        representation['text'] = instance.text
        representation['cooking_time'] = instance.cooking_time

        return representation


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = Favorite
        fields = ('recipe',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        favorite, created = Favorite.objects.get_or_create(**validated_data)
        if not created:
            raise serializers.ValidationError(
                'Этот рецепт уже добавлен в избранное.'
            )
        return favorite

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': instance.recipe.image.url,
            'cooking_time': instance.recipe.cooking_time,
        }


class ShoppingCartSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = ShoppingCart
        fields = ('recipe',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        shopping_cart, created = ShoppingCart.objects.get_or_create(
            **validated_data
        )
        if not created:
            raise serializers.ValidationError(
                'Этот рецепт уже добавлен в список покупок.'
            )
        return shopping_cart

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'image': instance.recipe.image.url,
            'cooking_time': instance.recipe.cooking_time,
        }
