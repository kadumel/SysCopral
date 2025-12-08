from django.db import models
from django.contrib.auth.models import User



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
        return str(self.nm_agregado) if self.nm_agregado else f"Agregado {self.placa}"
    
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
        return str(self.placa) if self.placa else f"Veículo {self.id}"
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
        return str(self.nm_item) if self.nm_item else f"Item {self.id_item}"
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
        return str(self.nm_servico) if self.nm_servico else f"Serviço {self.cd_servico}"
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
        veiculo_str = str(self.id_veiculo.placa) if self.id_veiculo and self.id_veiculo.placa else "Sem veículo"
        item_str = str(self.id_item.nm_item) if self.id_item and self.id_item.nm_item else "Sem item"
        return f"{veiculo_str} - {item_str} - {self.id_abastecimento}"
    
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
        return str(self.objeto) if self.objeto else f"Atualização {self.id}"
    
class OpeCategoria(models.Model):
    nome = models.CharField(max_length=150)

    class Meta:
        db_table = 'ope_categoria'
        verbose_name = 'categoria de lançamento'
        verbose_name_plural = 'categorias de lançamento'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return str(self.nome) if self.nome else f"Categoria {self.id}"


tipo_periodo = [
    ('M', 'Mensal'),
    ('S', 'Semanal'),
    ('Q', 'Quinzenal')
]


class Fechamento(models.Model):
   placa = models.ForeignKey(Veiculo, on_delete=models.CASCADE, db_column='id_veiculo', related_name='fechamentos_id_veiculo')
   data_fechamento = models.DateTimeField(db_column='DATAFECHAMENTO')
   cod_ag = models.CharField(max_length=20, db_column='COD_AG', blank=True, null=True)
   data_pagamento = models.DateField(null=True, blank=True)
   valor_total = models.FloatField(db_column='VALOR_TOTAL', blank=True, null=True)
   usuario = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario', related_name='fechamentos_id_usuario')
   dt_atualizacao = models.DateTimeField(auto_now=True)
   dt_criacao = models.DateTimeField(auto_now_add=True)

   class Meta:
        db_table = 'ope_fechamento'
        verbose_name = 'fechamento'
        verbose_name_plural = 'fechamentos'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]

   def __str__(self):
        return str(self.cod_ag) if self.cod_ag else f"Fechamento {self.data_fechamento.strftime('%d/%m/%Y')}"

class Lancamento(models.Model):
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE, db_column='id_veiculo', related_name='lancamentos_id_veiculo')
    categoria = models.ForeignKey(OpeCategoria, on_delete=models.CASCADE, db_column='id_categoria', related_name='lancamentos_id_categoria')
    data = models.DateField()
    # Natureza do lançamento: Entrada ou Saída
    NATUREZA_CHOICES = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
    ]
    natureza = models.CharField(max_length=1, choices=NATUREZA_CHOICES, default='S')
    periodo = models.CharField(max_length=10, choices=tipo_periodo, default='S')
    parcela = models.IntegerField(default=1)
    valor = models.FloatField()
    obs = models.TextField(blank=True, null=True)
    fechamento = models.ForeignKey(Fechamento, on_delete=models.CASCADE, null=True, blank=True)
    natureza = models.CharField(max_length=10, choices=[('R', 'Receita'), ('D', 'Despesa')], default='R')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario', related_name='lancamentos_id_usuario')
    dt_atualizacao = models.DateTimeField(auto_now=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_lancamento'
        verbose_name = 'lancamento'
        verbose_name_plural = 'lancamentos'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        veiculo_str = str(self.veiculo.placa.placa) if self.veiculo and self.veiculo.placa else "Sem veículo"
        categoria_str = str(self.categoria.nome) if self.categoria else "Sem categoria"
        usuario_str = str(self.usuario.username) if self.usuario else "Sem usuário"
        return f"{veiculo_str} - {categoria_str} - {self.data} - R$ {self.valor} - {usuario_str}"
    



class ContasReceber(models.Model):
    placa = models.ForeignKey(Veiculo, on_delete=models.CASCADE, db_column='id_veiculo', related_name='contas_receber_id_veiculo')
    data_fechamento = models.DateField()
    valor = models.FloatField()
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario_criado', related_name='contasareceber_criado_por')
    atualizado_por = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario_atualizado', related_name='contasareceber_atualizado_por')
    dt_atualizacao = models.DateTimeField(auto_now=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_contas_receber'
        verbose_name = 'contas receber'
        verbose_name_plural = 'contas receber'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return str(self.placa) if self.placa else f"Contas receber {self.data_fechamento.strftime('%d/%m/%Y')}"


class ItensContasReceber(models.Model):
    ordemServico = models.IntegerField(db_column='CDORDERSERVICO')
    cdServico = models.IntegerField(db_column='CDSERVICO')
    nmServico = models.CharField(max_length=255, db_column='NMSERVICO')
    data = models.DateTimeField(db_column='DATA')
    tipo = models.CharField(max_length=50, db_column='TIPO')
    cdItem = models.IntegerField(db_column='CDITEM')
    nmItem = models.CharField(max_length=255, db_column='NMITEM')
    qtde = models.FloatField(db_column='QTDE')
    unidade = models.CharField(max_length=20, db_column='UNIDADE')
    valor_unitario = models.FloatField(db_column='VALOR_UNITARIO')
    percentual = models.FloatField(db_column='PERCENTUAL')
    valor = models.FloatField(db_column='VALOR')
    total = models.FloatField(db_column='TOTAL')
    periodo = models.CharField(max_length=10)
    parcela = models.IntegerField()
    contas_receber = models.ForeignKey(ContasReceber, on_delete=models.CASCADE, null=True, blank=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'ope_contas_receber_itens'
        verbose_name = 'itens de contas receber'
        verbose_name_plural = 'itens de contas receber'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]

    def __str__(self):
        return f"OS {self.ordemServico} - {self.nmServico} - {self.placa} - {self.data.strftime('%Y-%m-%d') if self.data else ''}"


class VencContasReceber(models.Model):
    contas_receber = models.ForeignKey(ContasReceber, on_delete=models.CASCADE)
    fechamento = models.ForeignKey(Fechamento, on_delete=models.CASCADE, null=True, blank=True)
    seq_vencimento = models.IntegerField()
    data_vencimento = models.DateField()
    valor = models.FloatField()
    dt_atualizacao = models.DateTimeField(auto_now=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_contas_receber_vencimento'
        verbose_name = 'vencimento de contas receber'
        verbose_name_plural = 'vencimentos de contas receber'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]





class ContasPagar(models.Model):
    placa = models.ForeignKey(Veiculo, on_delete=models.CASCADE, db_column='id_veiculo', related_name='contas_a_pagar_id_veiculo')
    data_fechamento = models.DateField()
    valor = models.FloatField()
    fl_vlfixo = models.CharField(max_length=1, choices=[('S', 'Sim'), ('N', 'Não')], default='N', verbose_name='Valor fixo')
    valor_fixo = models.FloatField(verbose_name='Valor fixo', null=True, blank=True)
    criado_por = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario_criado', related_name='contasapagar_criado_por')
    atualizado_por = models.ForeignKey(User, on_delete=models.CASCADE, db_column='id_usuario_atualizado', related_name='contasapagar_atualizado_por')
    dt_atualizacao = models.DateTimeField(auto_now=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_contas_pagar'
        unique_together = ('placa', 'data_fechamento')
        verbose_name = 'contas pagar'
        verbose_name_plural = 'contas pagar'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return str(self.placa) if self.placa else f"Contas pagar {self.data_fechamento.strftime('%d/%m/%Y')}"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class ItensContasPagar(models.Model):
    empresa = models.CharField(max_length=3)
    codigo = models.CharField(max_length=10, unique=True)
    placa = models.CharField(max_length=10)
    data = models.DateField()
    act = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=1)
    trecho = models.CharField(max_length=10, null=True, blank=True)
    valor = models.FloatField(default=0)
    adiantamento = models.FloatField(default=0)
    outros = models.FloatField(default=0)
    saldo = models.FloatField(default=0)
    periodo = models.CharField(max_length=10, choices=tipo_periodo, default='S')
    parcela = models.IntegerField(default=1)
    contas_pagar = models.ForeignKey(ContasPagar, on_delete=models.CASCADE, null=True, blank=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_contas_pagar_itens'
        verbose_name = 'itens de contas pagar'
        verbose_name_plural = 'itens de contas pagar'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]
    def __str__(self):
        return f"OS {self.empresa} - {self.codigo} - {self.placa} - {self.data.strftime('%Y-%m-%d') if self.data else ''}"
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class VencContasPagar(models.Model):
    contas_pagar = models.ForeignKey(ContasPagar, on_delete=models.CASCADE, null=True, blank=True)
    fechamento = models.ForeignKey(Fechamento, on_delete=models.CASCADE, null=True, blank=True)
    seq_vencimento = models.IntegerField()
    data_vencimento = models.DateField()
    valor = models.FloatField()
    dt_atualizacao = models.DateTimeField(auto_now=True)
    dt_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ope_contas_pagar_vencimento'
        verbose_name = 'vencimento de contas pagar'
        verbose_name_plural = 'vencimentos de contas pagar'
        permissions = [('acessar_operacional', 'Pode acessar o módulo de operações')]