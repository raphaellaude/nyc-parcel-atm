from django.urls import path, register_converter
from data import views
from data.converters import LatConverter, LonConverter


register_converter(LatConverter, 'latitude')
register_converter(LonConverter, 'longitude')

urlpatterns = [
    path("single_year_pluto/<str:year>/<latitude:lat>/<longitude:lon>/", views.single_year_pluto, name='single_year_pluto'),
]
