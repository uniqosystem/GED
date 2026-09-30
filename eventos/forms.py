import re

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from django.forms import inlineformset_factory

from .models import CampoInscricao, Evento


def normalizar_cpf(valor):
	return re.sub(r'\D', '', valor or '')


def cpf_valido(valor):
	cpf = normalizar_cpf(valor)
	if len(cpf) != 11 or len(set(cpf)) == 1:
		return False

	soma = sum(int(digito) * (10 - indice) for indice, digito in enumerate(cpf[:9]))
	primeiro = (soma * 10 % 11) % 10
	if primeiro != int(cpf[9]):
		return False

	soma = sum(int(digito) * (11 - indice) for indice, digito in enumerate(cpf[:10]))
	segundo = (soma * 10 % 11) % 10
	return segundo == int(cpf[10])


class InscricaoForm(forms.Form):
	nome = forms.CharField(max_length=200, label='Nome completo', widget=forms.TextInput(attrs={'class': 'form-control'}))
	cpf = forms.CharField(max_length=14, label='CPF', widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric'}))
	email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'class': 'form-control'}))
	telefone = forms.CharField(max_length=30, label='Telefone', widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'tel'}))
	consentiu_lgpd = forms.BooleanField(
		label='Concordo com o uso dos meus dados para a finalidade desta inscrição.',
		required=True,
		widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
	)

	def __init__(self, *args, evento, **kwargs):
		self.evento = evento
		super().__init__(*args, **kwargs)
		for campo in evento.campos_adicionais.filter(ativo=True):
			self.fields[f'campo_{campo.chave}'] = forms.CharField(
				label=campo.nome,
				required=campo.obrigatorio,
				widget=forms.TextInput(attrs={'class': 'form-control'}),
			)

	def clean_cpf(self):
		cpf = normalizar_cpf(self.cleaned_data['cpf'])
		if not cpf_valido(cpf):
			raise forms.ValidationError('Informe um CPF válido.')
		return cpf

	def respostas_adicionais(self):
		return {
			nome: self.cleaned_data.get(nome, '')
			for nome in self.fields
			if nome.startswith('campo_')
		}


class EventoForm(forms.ModelForm):
	class Meta:
		model = Evento
		exclude = ('slug', 'criado_por')
		widgets = {
			'titulo': forms.TextInput(attrs={'class': 'form-control'}),
			'data_evento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
			'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
			'hora_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
			'local': forms.TextInput(attrs={'class': 'form-control'}),
			'palestrantes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
			'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
			'regras': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
			'carga_horaria': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.5'}),
			'inscricoes_encerram_em': forms.DateTimeInput(
				attrs={'type': 'datetime-local', 'class': 'form-control'},
				format='%Y-%m-%dT%H:%M',
			),
			'limite_inscricoes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
			'status': forms.Select(attrs={'class': 'form-select'}),
			'imagem': forms.ClearableFileInput(attrs={'class': 'form-control'}),
		}

	def clean_imagem(self):
		imagem = self.cleaned_data.get('imagem')
		if not imagem or not hasattr(imagem, 'read'):
			return imagem
		if imagem.size > settings.UPLOAD_MAX_SIZE:
			raise ValidationError('A imagem excede o limite permitido.')
		try:
			imagem.seek(0)
			with Image.open(imagem) as imagem_aberta:
				if imagem_aberta.format not in {'PNG', 'JPEG', 'GIF'}:
					raise ValidationError('Use uma imagem PNG, JPEG ou GIF.')
				imagem_aberta.verify()
		except (UnidentifiedImageError, OSError) as exc:
			raise ValidationError('O arquivo enviado não é uma imagem válida.') from exc
		finally:
			imagem.seek(0)
		return imagem


CampoInscricaoFormSet = inlineformset_factory(
	Evento,
	CampoInscricao,
	fields=('nome', 'chave', 'obrigatorio', 'ativo'),
	extra=1,
	can_delete=True,
)
