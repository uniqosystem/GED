from django import forms

from .models import RegistroPonto, Ocorrencia, PerfilFuncionario

class RegistroPontoForm(forms.ModelForm):
    class Meta:
        model = RegistroPonto
        fields = ['usuario', 'tipo', 'data_hora', 'latitude', 'longitude']
        widgets = {
            'data_hora': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'usuario': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
        }

class OcorrenciaForm(forms.ModelForm):
    class Meta:
        model = Ocorrencia
        fields = '__all__'
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class PerfilCompletoForm(forms.ModelForm):
    class Meta:
        model = PerfilFuncionario
        fields = ['cpf', 'status', 'horario_entrada', 'horario_saida']
        widgets = {
            'cpf': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.TextInput(attrs={'class': 'form-control'}),
            'horario_entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }