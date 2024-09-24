from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CustomUserViewSet,
                    TagViewSet,
                    RecipeViewSet,
                    IngredientViewSet)

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'tags', TagViewSet)
router.register(r'users', CustomUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
