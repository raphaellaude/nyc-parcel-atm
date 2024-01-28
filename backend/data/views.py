from django.http import HttpResponse

# Create your views here.
def single_year_pluto(request, year, lat, lon):
    return HttpResponse(f"Single year pluto {year} {lat} {lon}")
