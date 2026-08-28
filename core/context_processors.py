def usuario_setor(request):
    if request.user.is_authenticated:
        # Tenta buscar o setor do usuário pelo perfil ou atributo direto
        setor = None
        perfil = getattr(request.user, 'perfil', None)
        if perfil and hasattr(perfil, 'setor'):
            setor = perfil.setor
        elif hasattr(request.user, 'setor'):
            setor = request.user.setor
            
        return {'setor_usuario': setor}
    return {'setor_usuario': None}