from .access import Perfil, Setor
from .audit import LogAuditoria
from .documents import Documento, Prontuario
from .trash import RegistroLixeira
from . import signals

__all__ = [
    'Documento',
    'LogAuditoria',
    'Perfil',
    'Prontuario',
    'RegistroLixeira',
    'Setor',
]
