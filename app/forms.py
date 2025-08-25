from django import forms
from .models import Campos, OrdemServico
from django.contrib.admin.widgets import AdminDateWidget



class CamposForm(forms.ModelForm):
    class Meta:
        model = Campos
        fields = [
            'nome_placa',
            'data_inicial',
            'data_final',
            'selecao',
        ]

class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = "__all__"
