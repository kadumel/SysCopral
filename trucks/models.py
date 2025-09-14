# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

    
class TrucksVeiculos(models.Model):
    id = models.AutoField(primary_key=True)
    veiid = models.IntegerField(db_column='veiID', blank=True, null=True)  # Field name made lowercase.
    placa = models.CharField(max_length=7, blank=True, null=True)
    vs = models.FloatField(blank=True, null=True)
    tcmd = models.IntegerField(db_column='tCmd', blank=True, null=True)  # Field name made lowercase.
    tmac = models.CharField(db_column='tMac', max_length=20, blank=True, null=True)  # Field name made lowercase.
    ecmd = models.CharField(db_column='eCmd', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tp = models.IntegerField(blank=True, null=True)
    ta = models.IntegerField(blank=True, null=True)
    eqp = models.IntegerField(blank=True, null=True)
    mot = models.CharField(max_length=150, blank=True, null=True)
    prop = models.CharField(max_length=20, blank=True, null=True)
    die = models.CharField(db_column='dIE', max_length=20, blank=True, null=True)  # Field name made lowercase.
    loc = models.CharField(max_length=20, blank=True, null=True)
    ident = models.CharField(max_length=50, blank=True, null=True)
    vmanut = models.IntegerField(db_column='vManut', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'trucks_veiculos'




class TrucksResumoDiario(models.Model):
    placa = models.CharField(max_length=7, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    data = models.DateField(blank=True, null=True)
    diasemana = models.CharField(db_column='diaSemana', max_length=20, blank=True, null=True)  # Field name made lowercase.
    ligadoparado = models.CharField(db_column='ligadoParado', max_length=8, blank=True, null=True)  # Field name made lowercase.
    veimovi = models.CharField(db_column='veiMovi', max_length=8, blank=True, null=True)  # Field name made lowercase.
    iniciojornada = models.CharField(db_column='InicioJornada', max_length=8, blank=True, null=True)  # Field name made lowercase.
    fimjornada = models.CharField(db_column='FimJornada', max_length=8, blank=True, null=True)  # Field name made lowercase.
    jornada = models.CharField(db_column='Jornada', max_length=8, blank=True, null=True)  # Field name made lowercase.
    temponoturno = models.CharField(db_column='tempoNoturno', max_length=20, blank=True, null=True)  # Field name made lowercase.
    temponoturnoextra = models.CharField(db_column='tempoNoturnoExtra', max_length=20, blank=True, null=True)  # Field name made lowercase.
    estourojornada = models.CharField(db_column='estouroJornada', max_length=20, blank=True, null=True)  # Field name made lowercase.
    horaalmoco = models.CharField(db_column='horaAlmoco', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempoespera = models.CharField(db_column='tempoEspera', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempodescanso = models.CharField(db_column='tempoDescanso', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempodiurno = models.CharField(db_column='tempoDiurno', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempoextra = models.CharField(db_column='TempoExtra', max_length=20, blank=True, null=True)  # Field name made lowercase.
    dtalteracao = models.CharField(db_column='dtAlteracao', max_length=10, blank=True, null=True)  # Field name made lowercase.
    useralteracao = models.CharField(db_column='userAlteracao', max_length=50, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'trucks_ResumoDiario'



class TrucksImportadosExcel(models.Model):
    placa = models.CharField(max_length=7, blank=True, null=True)
    identificacao = models.CharField(max_length=30, blank=True, null=True)
    distpecorrido = models.CharField(db_column='distPecorrido', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempopadrao = models.CharField(db_column='tempoPadrao', max_length=20, blank=True, null=True)  # Field name made lowercase.
    velocidademedia = models.CharField(db_column='velocidadeMedia', max_length=20, blank=True, null=True)  # Field name made lowercase.
    tempomovimento = models.CharField(db_column='tempoMovimento', max_length=20, blank=True, null=True)  # Field name made lowercase.
    datahora = models.DateTimeField(db_column='dataHora', blank=True, null=True)  # Field name made lowercase.
    localizacao = models.TextField(blank=True, null=True)
    latitude = models.CharField(max_length=20, blank=True, null=True)
    longitude = models.CharField(max_length=20, blank=True, null=True)
    velocidade = models.IntegerField(blank=True, null=True)
    km = models.CharField(max_length=5, blank=True, null=True)
    parado = models.CharField(max_length=10, blank=True, null=True)
    tipomsg = models.CharField(db_column='tipoMsg', max_length=30, blank=True, null=True)  # Field name made lowercase.
    log = models.CharField(max_length=10, blank=True, null=True)
    modo_emergencia = models.CharField(db_column='modo_Emergencia', max_length=30, blank=True, null=True)  # Field name made lowercase.
    bateria = models.IntegerField(blank=True, null=True)
    dtimport = models.DateTimeField(db_column='dtImport', blank=True, null=True)  # Field name made lowercase.
    arquivo = models.CharField(max_length=100, blank=True, null=True)
    data_proximo = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'trucks_ImportadosExcel'


class TrucksPosicaoCarroApi(models.Model):
    id = models.AutoField(primary_key=True)
    mid = models.BigIntegerField(db_column='mId', blank=True, null=True)  # Field name made lowercase.
    veiid = models.IntegerField(db_column='veiID', blank=True, null=True)  # Field name made lowercase.
    dt = models.DateTimeField(blank=True, null=True)
    lat = models.CharField(max_length=10, blank=True, null=True)
    lon = models.CharField(max_length=10, blank=True, null=True)que 
    mun = models.CharField(max_length=50, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)
    rod = models.CharField(max_length=50, blank=True, null=True)
    rua = models.CharField(max_length=50, blank=True, null=True)
    vel = models.IntegerField(blank=True, null=True)
    ori = models.IntegerField(blank=True, null=True)
    tpmsg = models.IntegerField(db_column='tpMsg', blank=True, null=True)  # Field name made lowercase.
    dtinc = models.DateTimeField(db_column='dtInc', blank=True, null=True)  # Field name made lowercase.
    evtg = models.IntegerField(db_column='evtG', blank=True, null=True)  # Field name made lowercase.
    rpm = models.IntegerField(blank=True, null=True)
    odm = models.IntegerField(blank=True, null=True)
    lt = models.IntegerField(blank=True, null=True)
    mlog = models.CharField(db_column='mLog', max_length=10, blank=True, null=True)  # Field name made lowercase.
    pcnome = models.CharField(db_column='pcNome', max_length=50, blank=True, null=True)  # Field name made lowercase.
    mot = models.CharField(max_length=50, blank=True, null=True)
    motid = models.IntegerField(db_column='motID', blank=True, null=True)  # Field name made lowercase.
    prnome = models.CharField(db_column='prNome', max_length=50, blank=True, null=True)  # Field name made lowercase.
    status = models.IntegerField(blank=True, null=True)
    dtimport = models.DateTimeField(db_column='dtImport', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'trucks_posicaoCarroAPI'
