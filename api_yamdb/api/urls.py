from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


api_ver = 'v1'

router = DefaultRouter()
router.register('users', views.AdminViewSet)
router.register('auth/signup', views.SignUpViewSet)
router.register('titles', views.TitleViewSet)
router.register('genres', views.GenreViewSet)
router.register('categories', views.CategoryViewSet)
router.register(
    r'titles/(?P<title_id>\d+)/reviews',
    views.ReviewViewSet,
    basename='reviews'
)
router.register(
    r'titles/(?P<title_id>\d+)/reviews/(?P<review_id>\d+)/comments',
    views.CommentViewSet,
    basename='comments'
)

urlpatterns = [
    path(f'{api_ver}/users/me/', views.UserViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
    })),
    path(f'{api_ver}/', include(router.urls)),
    path(f'{api_ver}/auth/token/', views.GetTokenView.as_view()),
]
