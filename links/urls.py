from django.urls import path
# from django.views.generic import TemplateView

from . import views




urlpatterns = [
    # path("", views.indexLinks),
    path('', views.indexLinks, name='indexLinks'),
    path('painel/<int:id>', views.painel, name='painel'),
    path("reports/demo/", views.powerbi_report_view, name="powerbi-demo"),
    path("reports/refresh-token/", views.refresh_token_view, name="refresh-token"),

]
   

