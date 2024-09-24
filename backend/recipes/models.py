from django.db import models
from users.models import CustomUser


class Tag(models.Model):
    name = models.CharField(
        max_length=32,
        unique=True,
        verbose_name='Название',
        blank=False
    )
    slug = models.SlugField(
        max_length=32,
        unique=True,
        verbose_name='Slug',
        blank=False
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    update_date = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return f'Тег: {self.name}'


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128,
        verbose_name='Название',
        blank=False
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения',
        blank=False
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    update_date = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'Ингредиент: {self.name}'


class Recipe(models.Model):
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        max_length=256,
        verbose_name='Название',
        blank=False
    )
    image = models.ImageField(
        upload_to='recipes/',
        verbose_name='Изображение',
        blank=False
    )
    text = models.TextField(
        verbose_name='Описание',
        blank=False
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления (минут)',
        blank=False
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги',
        blank=True
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
        blank=False
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True
    )
    update_date = models.DateTimeField(
        verbose_name='Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return f'Рецепт: {self.name}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        blank=False
    )

    class Meta:
        unique_together = ('recipe', 'ingredient')
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return f'{self.amount} {self.ingredient.name} для {self.recipe.name}'


class Favorite(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_cart_by'
    )

    class Meta:
        unique_together = ('user', 'recipe')
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
