from django.contrib import admin
from .models import Acesso, Link
from datetime import datetime
# Register your models here.

admin.site.register(Acesso)


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('id','desc','link')
    list_filter = ('desc','link')
    search_fields = ('desc',)


