from django.contrib.auth import password_validation
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.constants import (
    AMOUNT_MIN_VALUE,
    RECIPES_LIMIT_DEFAULT,
    RECIPES_LIMIT_MIN_VALUE
)
from api.validators import (
    validate_cooking_time,
    validate_image,
    validate_ingredients,
    validate_subscription,
    validate_tags,
    validate_username
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)
from users.models import CustomUser, Subscription


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True, 'write_only': True},
        }

    def validate_username(self, value):
        return validate_username(value)

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


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
            return request.user.subscriptions.filter(author=obj).exists()
        return False

    def validate(self, attrs):
        if 'avatar' not in attrs or attrs['avatar'] is None:
            raise serializers.ValidationError(
                'Поле `avatar` обязательно.'
            )

        if isinstance(attrs['avatar'], str) and attrs['avatar'].strip() == '':
            raise serializers.ValidationError(
                'Поле `avatar` не может быть пустым.'
            )

        return attrs


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

        validate_subscription(user, author, recipes_limit)

        return data

    def create(self, validated_data):
        user = validated_data['user']
        author = validated_data['author']

        subscription = Subscription.objects.create(
            user=user,
            author=author
        )

        return subscription

    def to_representation(self, instance):
        request = self.context.get('request')
        user = (
            request.user
            if request and request.user.is_authenticated
            else None
        )
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
            'is_subscribed': Subscription.objects.filter(
                user=user,
                author=instance.author
            ).exists() if user else False,
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
    is_favorited = serializers.SerializerMethodField('get_is_favorited')
    is_in_shopping_cart = serializers.SerializerMethodField(
        'get_is_in_shopping_cart'
    )

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
        return validate_cooking_time(value)

    def validate_tags(self, tags):
        return validate_tags(tags)

    def validate_ingredients(self, ingredients):
        return validate_ingredients(ingredients)

    def validate_image(self, image):
        return validate_image(image)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])

        validate_ingredients(ingredients_data)
        validate_tags(tags_data)

        validated_data['author'] = self.context.get('request').user

        recipe = Recipe.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            ingredient = Ingredient.objects.get(id=ingredient_id)
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

        validate_ingredients(ingredients_data)
        validate_tags(tags_data)

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
            ingredient = Ingredient.objects.get(id=ingredient_id)
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=amount
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
