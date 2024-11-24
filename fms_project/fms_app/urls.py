from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet

router = DefaultRouter()
router.register(r'fms', ItemViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
