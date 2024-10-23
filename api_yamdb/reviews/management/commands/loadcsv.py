import csv
from django.conf import settings
from django.core.management.base import BaseCommand
from reviews.models import (
    Category, Comments, Genre, GenreTitle, Review, Title, User
)

MODELS_FILES = {
    User: 'users.csv',
    Category: 'category.csv',
    Genre: 'genre.csv',
    Title: 'titles.csv',
    GenreTitle: 'genre_title.csv',
    Review: 'review.csv',
    Comments: 'comments.csv'
}


class Command(BaseCommand):
    help = 'Загрузка файлов .csv в базу данных '

    def handle(self, *args, **options):
        for model, csv_file in MODELS_FILES.items():
            with open(
                f'{settings.BASE_DIR}/static/data/{csv_file}',
                'r',
                encoding='utf-8'
            ) as csvfile:
                reader = csv.DictReader(csvfile)
                model.objects.bulk_create(
                    model(**data) for data in reader)
                print(
                    f'Данные из файла {csv_file} загруженны в БД'
                    f' в таблицу модели {model.__name__}'
                )
        self.stdout.write(
            self.style.SUCCESS(
                'Все данные успешно загружены в базу!'
            ))
