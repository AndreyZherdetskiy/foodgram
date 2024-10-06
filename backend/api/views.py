import hashlib
from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_extra_fields.fields import Base64ImageField
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.constants import RECIPES_LIMIT_DEFAULT, UNIQUE_ID_LENGTH
from api.filters import RecipeFilter
from api.paginators import CustomPageNumberPagination
from api.permissions import IsAdminUserOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (
    ChangePasswordSerializer,
    CustomUserCreateSerializer,
    CustomUserSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeSerializer,
    ShoppingCartSerializer,
    SubscriptionSerializer,
    TagSerializer
)
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import CustomUser, Subscription


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__istartswith=name)
            queryset = queryset | Ingredient.objects.filter(
                name__icontains=name
            )
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminUserOrReadOnly,)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateUpdateSerializer
        elif self.action in ('list', 'retrieve'):
            return RecipeSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return (permissions.AllowAny(),)
        return (permissions.IsAuthenticated(), IsAuthorOrReadOnly())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link',
        permission_classes=(permissions.AllowAny,)
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        unique_string = f'{recipe.id}-{recipe.pub_date.isoformat()}'
        unique_id = hashlib.md5(
            unique_string.encode()
        ).hexdigest()[:UNIQUE_ID_LENGTH]

        domain = request.build_absolute_uri('/')[:-1]
        link = f'{domain}/recipes/s/{unique_id}/'

        return Response({'short-link': link}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=('get',),
        url_path='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated, IsAuthorOrReadOnly)
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart_items = ShoppingCart.objects.filter(user=user)
        ingredients = defaultdict(lambda: {'amount': 0, 'unit': None})

        for item in shopping_cart_items:
            recipe = item.recipe
            for recipe_ingredient in recipe.recipeingredient_set.all():
                ingredient = recipe_ingredient.ingredient
                ingredients[ingredient.name]['amount'] += (
                    recipe_ingredient.amount
                )
                if ingredients[ingredient.name]['unit'] is None:
                    ingredients[ingredient.name]['unit'] = (
                        ingredient.measurement_unit
                    )

        response_content = 'Список покупок:\n'
        for ingredient_name, data in ingredients.items():
            total_amount = data['amount']
            measurement_unit = data['unit']
            response_content += (
                f'{ingredient_name} — {total_amount} {measurement_unit}\n'
            )

        response = HttpResponse(response_content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='favorite',
        permission_classes=(permissions.IsAuthenticated, IsAuthorOrReadOnly)
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            serializer = FavoriteSerializer(
                data={'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            try:
                favorite_item = Favorite.objects.get(
                    user=request.user,
                    recipe=recipe
                )
                favorite_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Favorite.DoesNotExist:
                return Response(
                    {'detail': 'Этот рецепт не в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='shopping_cart',
        permission_classes=(permissions.IsAuthenticated, IsAuthorOrReadOnly)
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            serializer = ShoppingCartSerializer(
                data={'recipe': recipe.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        elif request.method == 'DELETE':
            try:
                shopping_item = ShoppingCart.objects.get(
                    user=request.user,
                    recipe=recipe
                )
                shopping_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ShoppingCart.DoesNotExist:
                return Response(
                    {'detail': 'Этот рецепт не в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action in ('create',):
            return CustomUserCreateSerializer
        return CustomUserSerializer

    def list(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=('get',),
        url_path='me',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def avatar(self, request):
        user = get_object_or_404(CustomUser, pk=request.user.pk)

        if request.method == 'PUT':
            avatar_serializer = CustomUserSerializer(
                instance=user,
                data=request.data,
                partial=True
            )
            avatar_serializer.fields['avatar'] = Base64ImageField()
            avatar_serializer.is_valid(raise_exception=True)
            avatar_serializer.save()

            return Response(
                {'avatar': avatar_serializer.data['avatar']},
                status=status.HTTP_200_OK
            )

        elif request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {'detail': 'Аватар не найден.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(
        detail=False,
        methods=('post',),
        url_path='set_password',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def set_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        url_path='subscriptions',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request):
        subscriptions = request.user.subscriptions.all()
        recipes_limit = request.query_params.get(
            'recipes_limit',
            RECIPES_LIMIT_DEFAULT
        )

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'recipes_limit': recipes_limit, 'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            subscriptions,
            many=True,
            context={'recipes_limit': recipes_limit, 'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        url_path='subscribe',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(CustomUser, pk=pk)

        if request.method == 'POST':
            recipes_limit = request.query_params.get(
                'recipes_limit',
                RECIPES_LIMIT_DEFAULT
            )
            subscription_data = {
                'user': request.user.id,
                'author': author.id
            }

            subscription_serializer = SubscriptionSerializer(
                data=subscription_data,
                context={'recipes_limit': recipes_limit}
            )
            subscription_serializer.is_valid(raise_exception=True)
            subscription = subscription_serializer.save()
            return Response(
                subscription_serializer.data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=request.user,
                author=author
            ).first()

            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
