from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.



class Link(models.Model):
    desc = models.CharField(max_length=40, default='')
    link = models.CharField(max_length=400)
    
    class Meta:
        # Managed = True
        db_table = 'Link'

    def __str__(self):
        return '{}'.format( self.desc)

class Acesso(models.Model):
    group = models.ForeignKey(Group, on_delete=models.PROTECT)
    link = models.ForeignKey(Link, on_delete=models.PROTECT)

    class Meta:
        db_table = 'Acesso'
        ordering = ['group__name']

    def __str__(self):
        return f'{self.group.name} - {self.link.desc}'

