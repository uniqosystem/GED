"""Leitura e apresentacao do historico de tramitacoes."""


def montar_historico_tramitacao(tramitacao):
    historicos = tramitacao.historicos.select_related(
        'setor_origem', 'remetente'
    ).prefetch_related('anexos').order_by('id')

    data_historico = []
    for historico in historicos:
        anexos_historico = historico.anexos.all() if hasattr(historico, 'anexos') else []
        lista_anexos = [
            {
                'nome': anexo.arquivo.name.split('/')[-1],
                'url': anexo.arquivo.url,
            }
            for anexo in anexos_historico
        ]
        data_historico.append(
            {
                'tipo': getattr(historico, 'tipo_movimentacao', 'Movimentação'),
                'setor': historico.setor_origem.nome if historico.setor_origem else '',
                'remetente': historico.remetente.get_full_name() or historico.remetente.username,
                'data': historico.data_envio.strftime('%d/%m/%Y %H:%M') if hasattr(historico, 'data_envio') else '',
                'titulo': tramitacao.titulo,
                'despacho': historico.despacho,
                'anexos': lista_anexos,
            }
        )

    return data_historico
