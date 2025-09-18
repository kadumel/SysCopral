from django import forms


class JornadaFilterForm(forms.Form):
    """
    Formulário para filtros da página de controle de jornadas
    """
    SELECAO_CHOICES = (
        ("placa", "Placa"),
        ("motorista", "Motorista"),
        ('todos', 'Todos')
    )
    
    nome_placa = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite a placa ou nome do motorista'
        })
    )
    
    data_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    data_final = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    selecao = forms.ChoiceField(
        choices=SELECAO_CHOICES,
        initial='todos',
        required=False,
        widget=forms.Select(attrs={
            'class': 'custom-select'
        })
    )
