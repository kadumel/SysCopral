from django.urls import path
# from django.views.generic import TemplateView

from . import views


urlpatterns = [
    # path("", views.indexLinks),
    path('', views.indexLinks, name='indexLinks'),
    path('painel/<int:id>', views.painel, name='painel'),

]
   

