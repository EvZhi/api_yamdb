from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (CreateModelMixin,
                                   RetrieveModelMixin,
                                   UpdateModelMixin)
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView

from . import permisions, serializers
from .filters import TitleFilter
from .mixin import CreateListDestroyMixin
from reviews.models import Category, Genre, Title, User


class SignUpViewSet(CreateModelMixin, GenericViewSet):
    """ViewSet, обслуживающий эндпоинт api/v1/auth/signup/."""

    queryset = User.objects.all()
    serializer_class = serializers.SignUpSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        """
        Модифицированный метод .create().

        В случае, если пользователя с заданными username и email
        не существует, то происходит его создание.
        В случае, если пользователь с заданными username и email
        существует, то сериализатор обновляет его confirmation_code.
        """
        try:
            user = User.objects.get(
                username=request.data.get('username'),
                email=request.data.get('email')
            )
            serializer = self.get_serializer(user, data=request.data)
        except User.DoesNotExist:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_200_OK, headers=headers
        )


class GetTokenView(TokenObtainPairView):
    """ViewSet для получения токенов."""

    serializer_class = serializers.GetTokenSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(
            {'token': serializer.validated_data['token']},
            status=status.HTTP_200_OK
        )


class AdminViewSet(ModelViewSet):
    """ViewSet для функционала админов."""

    queryset = User.objects.all()
    serializer_class = serializers.AdminUsersSerializer
    permission_classes = (permisions.AdminOnly,)
    pagination_class = LimitOffsetPagination
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    http_method_names = ('get', 'post', 'patch', 'delete', 'head')
    lookup_field = 'username'

    def perform_create(self, serializer):
        user = serializer.save()
        user.set_unusable_password()
        user.save()


class UserViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """ViewSet для просмотра пользователем своих данных."""

    serializer_class = serializers.UserSerializer
    permission_classes = (IsAuthenticated,)
    http_method_names = ('get', 'patch')
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return self.request.user

    def get_object(self):
        return self.request.user


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.select_related('category').prefetch_related(
        'genre').annotate(rating=Avg('reviews__score'))
    permission_classes = (permisions.AdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter
    pagination_class = LimitOffsetPagination
    http_method_names = ('get', 'post', 'patch', 'delete', 'head')

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return serializers.TitleReadSerializer
        return serializers.TitleSerializer


class BaseForGenreAndCategoryViewSet(
    CreateListDestroyMixin, viewsets.GenericViewSet
):
    permission_classes = (permisions.AdminOrReadOnly,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)
    pagination_class = LimitOffsetPagination
    lookup_field = 'slug'


class GenreViewSet(BaseForGenreAndCategoryViewSet):
    queryset = Genre.objects.all()
    serializer_class = serializers.GenreSerializer


class CategoryViewSet(BaseForGenreAndCategoryViewSet):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """Класс обработки отзывов."""

    serializer_class = serializers.ReviewSerializer
    pk_url_kwarg = 'review_id'
    permission_classes = (permisions.UserStaffOrReadOnly,)
    pagination_class = LimitOffsetPagination
    http_method_names = ('get', 'post', 'patch', 'delete', 'head')

    def get_title(self):
        """Забираю необходимое произведение."""
        return get_object_or_404(Title, pk=self.kwargs['title_id'])

    def get_queryset(self):
        return self.get_title().reviews.all()

    def perform_create(self, serializer):
        serializer.save(title=self.get_title(), author=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    """Класс обработки комментариев."""

    serializer_class = serializers.CommentSerializer
    permission_classes = (permisions.UserStaffOrReadOnly,)
    pagination_class = LimitOffsetPagination
    pk_url_kwarg = 'comment_id'
    http_method_names = ('get', 'post', 'patch', 'delete', 'head')

    def get_review(self):
        # Забираю отзыв.
        title = get_object_or_404(Title, pk=self.kwargs['title_id'])
        return get_object_or_404(title.reviews, pk=self.kwargs['review_id'])

    def get_queryset(self):
        return self.get_review().comments.select_related('author')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, review=self.get_review())
