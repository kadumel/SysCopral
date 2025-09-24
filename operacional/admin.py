from django.contrib import admin
from .models import OpeCategoria, Lancamento
# Register your models here.

@admin.register(OpeCategoria)
class OpeCategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    list_filter = ('nome',)

@admin.register(Lancamento)
class LancamentoAdmin(admin.ModelAdmin):
    list_display = ('veiculo__placa__placa', 'categoria__nome', 'data', 'valor', 'obs', 'usuario', 'dt_atualizacao', 'dt_criacao')
    exclude = ('usuario',)
    list_filter = ('categoria__nome', 'data', 'usuario')
    search_fields = ('veiculo__placa__placa', )


    # Para exibir o campo "placa" (do veículo) no formulário do admin, precisamos sobrescrever o formfield para o campo "veiculo".
    # Assim, o admin mostrará um select de placas (Agregado) ao invés do id do veículo.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "veiculo":
            from .models import Veiculo
            kwargs["queryset"] = Veiculo.objects.select_related('placa').all()
            formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
            # Altera o label de cada opção para mostrar a placa do agregado
            formfield.label_from_instance = lambda obj: obj.placa.placa if obj.placa else str(obj)
            return formfield
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Só define autor na criação
            obj.usuario = request.user
        super().save_model(request, obj, form, change)