from django.db import models




# Create your models here.
class Agregado(models.Model):
    placa = models.CharField(max_length=10, primary_key=True)
    cnpjcpf = models.CharField(max_length=14, blank=True, null=True)
    nm_agregado = models.CharField(max_length=150)
    dt_atualizacao = models.DateTimeField()

    class Meta:
        db_table = 'ope_agregado'
        verbose_name = 'agregado'
        verbose_name_plural = 'agregados'

        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    
    def __str__(self):
        return self.nm_agregado
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Veiculo(models.Model):
    placa = models.ForeignKey(Agregado, on_delete=models.CASCADE, to_field='placa', db_column='placa', related_name='veiculos_placa')
    id_veiculo = models.IntegerField(primary_key=True)
    cd_veiculo = models.IntegerField()
    cd_frota = models.IntegerField()
    nm_frota = models.CharField(max_length=150)
    cd_centro_custo = models.IntegerField()
    nm_centro_custo = models.CharField(max_length=150)
    cnpjcpf = models.CharField(max_length=14, blank=True, null=True)
    dt_inativacao = models.DateField(blank=True, null=True)
    dt_atualizacao  = models.DateTimeField()

    class Meta:
        db_table = 'ope_veiculo'
        verbose_name = 'veículo'
        verbose_name_plural = 'veículos'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return self.placa
    def save(self, *args, **kwargs):
        self.placa = self.placa.upper()
        super().save(*args, **kwargs)

    
class Item(models.Model):
    id_item = models.IntegerField(primary_key=True)
    cd_sistema = models.IntegerField(blank=True, null=True)
    nm_sistema = models.CharField(max_length=150, blank=True, null=True)
    cd_grupo = models.IntegerField(blank=True, null=True)
    nm_grupo = models.CharField(max_length=150, blank=True, null=True)
    rf_item = models.CharField(max_length=20, blank=True, null=True)
    pro_codigo = models.CharField(max_length=20, blank=True, null=True)
    nm_item = models.CharField(max_length=150)
    unidade = models.CharField(max_length=10)
    vl_frota = models.FloatField(blank=True, null=True)
    vl_sistema = models.FloatField(blank=True, null=True)
    percentual = models.FloatField(blank=True, null=True)
    dt_atualizacao = models.DateTimeField()

    class Meta:
        db_table = 'ope_item'
        verbose_name = 'item'
        verbose_name_plural = 'itens'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return self.nm_item
    def save(self, *args, **kwargs):
        self.nm_item = self.nm_item.upper()
        super().save(*args, **kwargs)

class Servico(models.Model):
    cd_tipo_servico = models.IntegerField(blank=True, null=True)
    nm_tipo_servico = models.CharField(max_length=150, blank=True, null=True)
    cd_servico = models.IntegerField()
    nm_servico = models.CharField(max_length=255)
    valor = models.FloatField(blank=True, null=True)
    dt_atualizacao = models.DateTimeField()

    class Meta:
        db_table = 'ope_servico'
        verbose_name = 'serviço'
        verbose_name_plural = 'serviços'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return self.nm_servico
    def save(self, *args, **kwargs):
        self.nm_servico = self.nm_servico.upper()
        super().save(*args, **kwargs)



class Abastecimento(models.Model):
    id = models.AutoField(primary_key=True)
    id_veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, db_column='id_veiculo', related_name='abastecimentos_id_veiculo')
    id_item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='id_item', related_name='abastecimentos_id_item')
    id_abastecimento = models.IntegerField()
    dt_abastecimento = models.DateTimeField(blank=True, null=True)
    cd_ponto_apoio = models.IntegerField(blank=True, null=True)
    qt_litros = models.FloatField(blank=True, null=True)
    qt_litros_ant = models.FloatField(blank=True, null=True)
    qt_km = models.FloatField(blank=True, null=True)
    qt_km_ant = models.FloatField(blank=True, null=True)
    total_km = models.FloatField(blank=True, null=True)
    vl_litro = models.FloatField(blank=True, null=True)
    dt_atualizacao = models.DateTimeField()

    class Meta:
        db_table = 'ope_abastecimento'
        verbose_name = 'abastecimento'
        verbose_name_plural = 'abastecimentos'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
        # Adicionar índices para melhorar performance
        indexes = [
            models.Index(fields=['dt_abastecimento']),
            models.Index(fields=['id_veiculo']),
            models.Index(fields=['id_item']),
            models.Index(fields=['qt_litros']),
            models.Index(fields=['total_km']),
        ]
    
    def __str__(self):
        return f"{self.id_veiculo.placa} - {self.id_item.nm_item} - {self.id_abastecimento}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)



class Atualizações(models.Model):
    id = models.AutoField(primary_key=True)
    objeto = models.CharField(max_length=150)
    dt_atualizacao = models.DateTimeField()

    class Meta:
        db_table = 'atualizacoes'
        verbose_name = 'atualização'
        verbose_name_plural = 'atualizações'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return self.objeto
    

