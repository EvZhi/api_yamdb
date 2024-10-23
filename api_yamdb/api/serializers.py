from datetime import datetime
from random import randint
from smtplib import SMTPException

from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.tokens import AccessToken

from reviews.models import Category, Comments, Genre, Review, Title, User


EMAIL_SUBJECT = 'Код подтверждения'
EMAIL_SOURCE = 'from yamdb@mail.com'
EMAIL_ERROR = 'Произошла следующая ошибка при попытке отправки письма:\n'


class ValidateUsernameMixin:
    """Миксин, запрещающий пользователю создать username "me"."""

    def validate_username(self, value):
        if value.lower() == 'me':
            raise serializers.ValidationError(
                'Username me невозможно использовать.'
            )
        return value


class BaseUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name',
                  'last_name', 'bio', 'role')


class SignUpSerializer(ValidateUsernameMixin, serializers.ModelSerializer):
    """Сериализатор для эндпоинта api/v1/auth/signup/"""

    class Meta:
        model = User
        fields = ('username', 'email')
        read_only_fields = ('password',)

    def create(self, validated_data):
        """Метод create создаёт нового пользователя."""
        username = validated_data.get('username')
        email = validated_data.get('email')
        user, _ = User.objects.get_or_create(
            username=username,
            email=email,
        )
        confirmation_code = self.send_code(email)
        user.confirmation_code = confirmation_code
        user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        """Метод .update() создаёт пользователю новый код."""
        confirmation_code = self.send_code(validated_data.get('email'))
        instance.confirmation_code = confirmation_code
        instance.save()
        return instance

    def send_code(self, recipient_email):
        """Отвечает за создание кода подтверждения и отправку писем.
        Функция randint создаёт 6-значный код.
        Отправка письма осуществляется на почту, которую указал пользователь
        """
        confirmation_code = randint(100000, 999999)
        message = f'Код для получения токена - {confirmation_code}'
        try:
            send_mail(
                EMAIL_SUBJECT,
                message,
                EMAIL_SOURCE,
                (recipient_email,),
                fail_silently=True
            )
        except SMTPException as error:
            raise APIException(EMAIL_ERROR + error)
        return confirmation_code


class GetTokenSerializer(serializers.Serializer):
    """Сериализатор для получения пользователем Access Token."""
    username = serializers.CharField(write_only=True)
    confirmation_code = serializers.IntegerField(write_only=True)

    def validate(self, data):
        user = get_object_or_404(User, username=data['username'])
        if data['confirmation_code'] != user.confirmation_code:
            raise serializers.ValidationError('Неверный код подтверждения')
        data['token'] = str(AccessToken.for_user(user))
        return data


class AdminUsersSerializer(ValidateUsernameMixin, BaseUserSerializer):
    """Позоволяет админу взаимодейстовать с данными пользователей"""

    class Meta(BaseUserSerializer.Meta):
        read_only_fields = ('password',)


class UserSerializer(ValidateUsernameMixin, BaseUserSerializer):
    """Позволяет пользователю взаимодействовать со своими данными."""

    class Meta(BaseUserSerializer.Meta):
        read_only_fields = ('password', 'role')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('name', 'slug')
        lookup_field = 'slug',


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('name', 'slug')
        lookup_field = 'slug',


class TitleSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(read_only=True)
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field='slug'
    )
    genre = serializers.SlugRelatedField(
        queryset=Genre.objects.all(),
        many=True,
        slug_field='slug'
    )

    class Meta:
        fields = (
            'id', 'name', 'year', 'rating', 'description', 'genre', 'category'
        )
        model = Title

    def to_representation(self, instance):
        return TitleReadSerializer(instance).data

    def validate_year(self, value):
        if value > datetime.today().year:
            raise serializers.ValidationError(
                'Нельзя добавлять произведения, которые еще не вышли.'
            )
        return value

    def validate_genre(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле genre не может быть пустым'
            )
        return value


class TitleReadSerializer(serializers.ModelSerializer):
    rating = serializers.IntegerField(read_only=True, default=None)
    category = CategorySerializer(read_only=True)
    genre = GenreSerializer(read_only=True, many=True)

    class Meta:
        fields = (
            'id', 'name', 'year', 'rating', 'description', 'genre', 'category'
        )
        model = Title


class AuthorForReviewAndCommentSerializer(serializers.ModelSerializer):
    """Миксин для переопределения поля автора."""

    author = serializers.SlugRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault(),
        slug_field='username')


class CommentSerializer(AuthorForReviewAndCommentSerializer):
    """Сериализатор для комментариев."""

    class Meta:
        """Мета."""

        model = Comments
        fields = ('id', 'text', 'author', 'pub_date')

    def validate(self, data):
        """Валидация."""
        text = data.get('text')
        if not text:
            raise serializers.ValidationError(
                'Текст комментария не может быть пустым.'
            )
        return data


class ReviewSerializer(AuthorForReviewAndCommentSerializer):
    """Сериализатор для отзывов."""

    class Meta:
        """Мета."""

        model = Review
        fields = ('id', 'text', 'author', 'score', 'pub_date')

    def validate(self, data):
        author = self.context['request'].user
        title_id = self.context['view'].kwargs['title_id']
        title = get_object_or_404(Title, pk=title_id)

        if (
            Review.objects.filter(author=author, title=title).exists()
            and self.context['request'].method != 'PATCH'
        ):
            raise serializers.ValidationError(
                'Нельзя оставить более одного отзыва одним автором')
        return data
