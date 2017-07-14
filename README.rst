=====
django-orientdb-api
=====

This package is a library for working with OrientDB's API through the Django ORM. While functionality is a bit limited currently (fairly basic CRUD operations), in a future version it should be expected that this library will be extended for usage within the context of the Django REST framework specifically.

Quick start
-----------

1. Add "django_orientdb" to INSTALLED_APPS:
  INSTALLED_APPS = {
    ...
    'django_orientdb'
  }

2. Add the configuration settings for OrientDB to your settings.py file

DJANGORIENT_SETTINGS = {
    'host': 'localhost',
    'port': '2480',
    'username': 'root',
    'password': 'root',
    'name': 'TestDB',
}

3. Import models into your models.py file. Ensure that this schema matches the schema you have created in OrientDB studio

    # models.py
    from django_orientdb.models import *

    class Person(DjangorientNode):
        name = String()
        age = Integer()

    class Animal(DjangorientNode):
        nickname = String()

    class Owns(DjangorientEdge):
        years_owned = Integer()


4. Run `python manage.py makemigrations` and `python manage.py migrate` to create orientDB models


