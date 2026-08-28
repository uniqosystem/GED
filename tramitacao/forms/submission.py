from django import forms
from django.contrib.auth.models import User

from core.models import Setor

from ..models import Tramitacao


class TramitacaoForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        choices=Tramitacao.TIPO_DOCUMENTO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control js-form-field'})
    )
    titulo = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Solicitação de Equipamentos'})
    )
    setor_destino = forms.MultipleChoiceField(
        widget=forms.SelectMultiple(attrs={'class': 'form-control js-setor-select', 'multiple': 'multiple'}),
        required=True,
        label="Setor(es) de Destino"
    )
    usuario_destino = forms.MultipleChoiceField(
        widget=forms.SelectMultiple(attrs={'class': 'form-control js-user-select', 'multiple': 'multiple'}),
        required=False,
        label="Usuário(s) de Destino (Opcional)"
    )
    aguardar_resposta = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    exige_assinatura = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    data_limite_resposta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    despacho = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Digite o despacho...'})
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Observações adicionais (opcional)...'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lista_setores = [('todos', '-- SELECIONAR TODOS OS SETORES --')] + [(str(s.id), s.nome) for s in Setor.objects.all()]
        self.fields['setor_destino'].choices = lista_setores
        lista_usuarios = [(str(u.id), u.get_full_name() or u.username) for u in User.objects.all()]
        self.fields['usuario_destino'].choices = lista_usuarios

    def clean_usuario_destino(self):
        return self.cleaned_data.get('usuario_destino', [])