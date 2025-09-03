from django.db import models

class Campos(models.Model):
    SELECAO_CHOICES = (
        ("placa", "Placa"),
        ("motorista", "Motorista"),
        ('todos', 'Todos')
    )
    nome_placa = models.CharField(max_length=100)
    data_inicial = models.DateField()
    data_final = models.DateField()
    selecao = models.CharField(max_length=12, choices=SELECAO_CHOICES)


class OrdemServico(models.Model):
    data = models.CharField(max_length=10, null=True, blank=True)
    placa = models.CharField(max_length=10, null=True, blank=True)
    os = models.CharField(max_length=30, null=True, blank=True)
    dtInclusao = models.CharField(max_length=10, null=True, blank=True)
    userInclusao = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'OrdemServico'



class DummyRH(models.Model):
    pass

    class Meta:
        managed = False
        db_table = 'DummyRH'
        permissions = [('acessar_rh', 'Pode acessar o módulo de RH')]

    def __str__(self):
        return self.permission
    
class DummyDP(models.Model):
    pass

    class Meta:
        managed = False
        db_table = 'DummyDP'
        permissions = [('acessar_dp', 'Pode acessar o módulo de DP')]

    def __str__(self):
        return self.permission