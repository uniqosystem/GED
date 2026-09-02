import hashlib
import os

from django.conf import settings
from django.core.cache import cache

from .file_services import usuario_pode_acessar_caminho


def _chave_cache_diretorio(caminho, usuario, data_modificacao):
    chave_base = hashlib.sha256(os.path.abspath(caminho).encode()).hexdigest()
    if getattr(usuario, 'is_authenticated', False):
        nomes_permissoes = {
            str(grupo.name).lower().strip() for grupo in usuario.groups.all()
        }
        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.setor:
            nomes_permissoes.add(str(perfil.setor.nome).lower().strip())
        nomes_permissoes = sorted(nomes_permissoes)
        identidade = hashlib.sha256(
            ('|'.join(nomes_permissoes) or 'sem-grupos').encode('utf-8')
        ).hexdigest()
        identidade = f"u{usuario.pk}:{identidade}"
    else:
        identidade = 'anon'
    return f'ged:diretorio:{chave_base}:{data_modificacao}:{identidade}'


def listar_itens_diretorio(caminho, modulo, usuario):
    try:
        data_modificacao = os.stat(caminho).st_mtime_ns
    except OSError:
        return []

    chave_cache = _chave_cache_diretorio(caminho, usuario, data_modificacao)
    itens = cache.get(chave_cache)
    if itens is None:
        itens = []
        with os.scandir(caminho) as entradas:
            for entrada in entradas:
                if entrada.name == '.lixeira':
                    continue
                if entrada.is_dir():
                    itens.append({'nome': entrada.name, 'tipo': 'pasta', 'tamanho': '-', 'caminho': entrada.path, 'ordem': 0})
                elif entrada.is_file() and modulo != 'setores-raiz':
                    tamanho = round(entrada.stat().st_size / 1024, 2)
                    itens.append({'nome': entrada.name, 'tipo': 'arquivo', 'tamanho': f'{tamanho} KB', 'caminho': entrada.path, 'ordem': 1})
        cache.set(chave_cache, itens, timeout=300)

    if modulo not in {'setores', 'setores-raiz'}:
        return list(itens)
    return [item for item in itens if usuario_pode_acessar_caminho(usuario, item['caminho'])]


def realizar_busca_diretorio(termo_busca, modulo, usuario=None):
    nome_dir = 'PESSOA FISICA' if modulo == 'pessoa-fisica' else 'PESSOA JURIDICA'
    caminho_base = os.path.join(settings.GED_BASE_DIR, nome_dir)
    if usuario and not usuario_pode_acessar_caminho(usuario, caminho_base):
        return []

    resultados = []
    if os.path.exists(caminho_base):
        for nome_pasta in os.listdir(caminho_base):
            if termo_busca.lower() in nome_pasta.lower():
                caminho_completo = os.path.join(caminho_base, nome_pasta)
                if os.path.isdir(caminho_completo):
                    resultados.append({'nome': nome_pasta, 'modulo': modulo, 'label': 'PF' if modulo == 'pessoa-fisica' else 'PJ', 'caminho': caminho_completo, 'tipo': 'pasta'})
    return resultados