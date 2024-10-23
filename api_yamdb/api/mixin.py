from rest_framework import mixins


class CreateListDestroyMixin(mixins.CreateModelMixin,
                             mixins.ListModelMixin,
                             mixins.DestroyModelMixin):
    "Кастомный миксин класс."
    pass
