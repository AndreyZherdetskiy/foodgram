from django.contrib import admin

from recipes.forms import IngredientInlineForm, RecipeForm
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)


class IngredientInline(admin.TabularInline):
    model = RecipeIngredient
    form = IngredientInlineForm
    extra = 1


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeForm
    inlines = (IngredientInline,)
    list_display = ('name', 'author', 'get_favorites_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)

    def get_favorites_count(self, obj):
        return obj.favorited_by.count()
    get_favorites_count.short_description = 'Количество добавлений в избранное'


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
