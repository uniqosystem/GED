from django import forms
from django.contrib.auth.models import User


class RespostaTramitacaoForm(forms.Form):
    despacho = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'})
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )
    aguardar_resposta = forms.BooleanField(required=False)
    usuario_destino = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario_destino'].choices = [
            ('', 'Todos os usuários do setor')
        ] + [
            (str(user.id), user.get_full_name() or user.username)
            for user in User.objects.filter(is_active=True).order_by('username')
        ]