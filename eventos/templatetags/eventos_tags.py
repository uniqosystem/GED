from django import template

register = template.Library()


@register.filter
def mascarar_cpf(valor):
    cpf = ''.join(caractere for caractere in str(valor or '') if caractere.isdigit())
    if len(cpf) != 11:
        return valor
    return f'{cpf[:3]}.***.***-{cpf[-2:]}'
