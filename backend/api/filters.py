import django_filters

from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(
        field_name='author_id',
        lookup_expr='exact'
    )
    tags = django_filters.CharFilter(field_name='tags__slug', lookup_expr='in')
    is_favorited = django_filters.BooleanFilter(method='filter_favorited')
    is_in_shopping_cart = django_filters.BooleanFilter(method='filter_in_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'tags', 'is_favorited', 'is_in_shopping_cart']

    def filter_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorited_by__user=self.request.user)
        return queryset

    def filter_in_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(in_cart_by__user=self.request.user)
        return queryset
