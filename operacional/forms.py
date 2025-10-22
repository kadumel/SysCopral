from django import forms
from django.contrib.auth.models import User
from .models import Lancamento, Veiculo, OpeCategoria

class LancamentoForm(forms.ModelForm):
    class Meta:
        model = Lancamento
        fields = ['veiculo', 'categoria', 'data', 'periodo', 'parcela', 'valor', 'obs']
        widgets = {
            'veiculo': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'data': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'periodo': forms.Select(attrs={
                'class': 'form-select'
            }),
            'parcela': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'value': '1'
            }),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
            'obs': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações (opcional)'
            })
        }
        labels = {
            'veiculo': 'Veículo',
            'categoria': 'Categoria',
            'data': 'Data',
            'periodo': 'Período',
            'parcela': 'Parcela',
            'valor': 'Valor (R$)',
            'obs': 'Observações'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar veículos por placa
        self.fields['veiculo'].queryset = Veiculo.objects.select_related('placa').filter(
            dt_inativacao__isnull=True
        ).order_by('placa__placa')
        
        # Ordenar categorias por nome
        self.fields['categoria'].queryset = OpeCategoria.objects.all().order_by('nome')
        
        # Customizar labels dos veículos para mostrar placa e agregado
        veiculo_choices = [(v.id_veiculo, f"{v.placa.placa} - {v.placa.nm_agregado}") 
                          for v in self.fields['veiculo'].queryset]
        self.fields['veiculo'].choices = [('', '---------')] + veiculo_choices

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        return valor

    def clean_parcela(self):
        parcela = self.cleaned_data.get('parcela')
        if parcela is not None and parcela < 1:
            raise forms.ValidationError('A parcela deve ser maior ou igual a 1.')
        return parcela