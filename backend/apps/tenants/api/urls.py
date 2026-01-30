from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'products', ProductViewSet, basename='product')

app_name = 'tenants'

urlpatterns = [
    path('', include(router.urls)),
]
