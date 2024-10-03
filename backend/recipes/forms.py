from django import forms

from api.constants import AMOUNT_MIN_VALUE, COOKING_TIME_MIN_VALUE
from recipes.models import Ingredient, Recipe, RecipeIngredient


class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = (
            'author',
            'name',
            'image',
            'text',
            'cooking_time',
            'tags',
            'ingredients'
        )

    def clean_cooking_time(self):
        """Валидация времени приготовления."""
        cooking_time = self.cleaned_data['cooking_time']
        if cooking_time < COOKING_TIME_MIN_VALUE:
            raise forms.ValidationError(
                'Время приготовления должно быть больше 0'
            )
        return cooking_time

    def clean_tags(self):
        """Валидация тегов."""
        tags = self.cleaned_data['tags']
        if not tags:
            raise forms.ValidationError(
                'Необходимо отметить минимум один тег.'
            )
        if len(tags) != len(set(tags)):
            raise forms.ValidationError(
                'Дублирование тегов не допускается.'
            )
        return tags

    def clean_image(self):
        """Валидация изображения."""
        image = self.cleaned_data['image']
        if image is None or not image:
            raise forms.ValidationError(
                'Это поле не может быть пустым.'
            )
        return image


class IngredientInlineForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredient
        fields = ('ingredient', 'amount')

    def clean_ingredient(self):
        """Валидация ингредиента."""
        ingredient = self.cleaned_data.get('ingredient')

        if ingredient is None or not ingredient:
            raise forms.ValidationError(
                'Необходимо предоставить хотя бы один ингредиент.'
            )

        if not Ingredient.objects.filter(id=ingredient.id).exists():
            raise forms.ValidationError(
                f'Ингредиент с id {ingredient.id} не существует.'
            )

        recipe = self.instance.recipe if self.instance.pk else None

        if recipe:
            existing_ingredients = recipe.recipeingredient_set.exclude(
                pk=self.instance.pk
            )
            if existing_ingredients.filter(ingredient=ingredient).exists():
                raise forms.ValidationError(
                    'Дублирование ингредиентов не допускается.'
                )

        return ingredient

    def clean_amount(self):
        """Валидация количества ингредиента."""
        amount = self.cleaned_data.get('amount')

        if amount is None or amount < AMOUNT_MIN_VALUE:
            raise forms.ValidationError(
                'Ингредиент должен иметь положительное количество.'
            )

        return amount

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('ingredient'):
            raise forms.ValidationError('Это поле обязательно для заполнения.')
        if not cleaned_data.get('amount'):
            raise forms.ValidationError('Это поле обязательно для заполнения.')
        return cleaned_data
