from .action_views import (
    assinar_tramitacao,
    devolver_tramitacao,
    editar_tramitacao,
    excluir_tramitacao_devolvida,
    finalizar_tramitacao,
    obter_tramitacao_autorizada,
    receber_tramitacao,
    responder_tramitacao,
)
from .api_views import (
    ajax_usuarios_setores,
    api_historico_tramitacao,
    listar_anexos_json,
    verificar_notificacoes,
)
from .inbox_views import caixa_entrada, nova_tramitacao
from .destinations import setor_destino_unico, usuario_destino_unico
