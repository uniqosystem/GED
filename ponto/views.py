import pandas as pd
import logging
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User 
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import date
from django.conf import settings

from datetime import date, datetime, timedelta

from .models import RegistroPonto, Ocorrencia, PerfilFuncionario, Contracheque
from .forms import OcorrenciaForm, RegistroPontoForm, PerfilCompletoForm
from .utils import calcular_distancia, CRFPB_LAT, CRFPB_LON
from .permissions import is_ponto_rh

logger = logging.getLogger(__name__)

def login_view(request):
    if request.method == 'POST':
        user_input = request.POST.get('username')
        pass_input = request.POST.get('password')
        logger.info(f"Tentativa de login para o usuário: {user_input}")
        
        user = authenticate(request, username=user_input, password=pass_input)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.warning(f"Login realizado com SUCESSO. Redirecionando...")
                return redirect('registrar_ponto')
            else:
                logger.warning(f"{user_input} inativo.")
        else:
            logger.warning(f"Falha de autenticação para o usuário: {user_input}")
            
    return render(request, 'ponto/login.html')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required
def registrar_ponto(request):
    IP_AUTORIZADO = "177.83.198.206"
    IP_RECEBIDO = get_client_ip(request)

    if request.method == 'POST':
        # Lista de IPs que você quer liberar durante o desenvolvimento
        IPs_LIBERADOS_DESENVOLVIMENTO = [
            "206.42.42.148", 
            "2804:14c:da96:9344:f569:39f1:4998:5c79",
            "2804:14c:da96:9344:3aee:a36a:3467:1cbf",
            "2804:14c:da96:9344:a6a5:d6af:d53:a24d"
        ]

        # Lógica de bloqueio
        if not settings.DEBUG: 
            # Em produção, só aceita o IP fixo da empresa
            if IP_RECEBIDO != IP_AUTORIZADO:
                messages.error(request, "Acesso negado: Rede não autorizada.")
                return redirect('registrar_ponto')
        else:
            # Em desenvolvimento, aceita o fixo OU os IPs do seu notebook/celular
            if IP_RECEBIDO != IP_AUTORIZADO and IP_RECEBIDO not in IPs_LIBERADOS_DESENVOLVIMENTO:
                messages.error(request, f"IP não autorizado: {IP_RECEBIDO}")
                return redirect('registrar_ponto')

        # 2. Captura e validação de dados
        try:
            lat = float(request.POST.get('latitude', 0))
            lon = float(request.POST.get('longitude', 0))
            tipo = request.POST.get('tipo')
        except (ValueError, TypeError):
            messages.error(request, "Erro nos dados de localização.")
            return redirect('registrar_ponto')

        # 3. Cálculo de distância
        distancia = calcular_distancia(lat, lon, CRFPB_LAT, CRFPB_LON)
        
        if distancia <= 100:
            RegistroPonto.objects.create(
                usuario=request.user,
                tipo=tipo,
                latitude=lat,
                longitude=lon
            )
            messages.success(request, "Ponto registrado com sucesso!")
        else:
            messages.error(request, f"Fora do raio permitido! (Distância: {int(distancia)}m)")
            
        return redirect('registrar_ponto')
        
    return render(request, 'ponto/registrar.html')

@login_required
def exportar_ponto(request):
    if not is_ponto_rh(request.user):
        return redirect('registrar_ponto')

    # Filtros - TROQUEI 'user' POR 'usuario'
    nome = request.GET.get('nome')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    queryset = RegistroPonto.objects.all()
    if nome: queryset = queryset.filter(usuario__username=nome) # AQUI
    if data_inicio: queryset = queryset.filter(data_hora__date__gte=data_inicio)
    if data_fim: queryset = queryset.filter(data_hora__date__lte=data_fim)

    # Pegamos os dados - TROQUEI 'user' POR 'usuario'
    registros = queryset.values('usuario__username', 'data_hora', 'tipo', 'usuario_id') # AQUI
    df = pd.DataFrame(list(registros))
    if df.empty: return redirect('painel_rh')

    # Processa datas
    df['data_hora'] = pd.to_datetime(df['data_hora']).dt.tz_localize(None)
    df['data'] = df['data_hora'].dt.date
    df['hora'] = df['data_hora'].dt.time

    # Pivota - TROQUEI 'user' POR 'usuario'
    df = df.pivot_table(
        index=['usuario__username', 'data'], 
        columns='tipo', 
        values='hora', 
        aggfunc='first'
    ).reset_index()

    # Cálculo dinâmico - TROQUEI 'user' POR 'usuario'
    def calcular_jornada_completa(row):
        try:
            # Pega horários do dataframe
            ent = datetime.strptime(str(row['ENTRADA']), '%H:%M:%S')
            alm_s = datetime.strptime(str(row['ALMOCO_SAIDA']), '%H:%M:%S')
            alm_r = datetime.strptime(str(row['ALMOCO_RETORNO']), '%H:%M:%S')
            sai = datetime.strptime(str(row['SAIDA']), '%H:%M:%S')
            
            # Calcula períodos
            periodo1 = (alm_s - ent).total_seconds() / 3600
            periodo2 = (sai - alm_r).total_seconds() / 3600
            total_trabalhado = periodo1 + periodo2
            
            # Jornada padrão (8h - exemplo)
            jornada_padrao = 8.0 
            
            extras = max(0, total_trabalhado - jornada_padrao)
            faltas = max(0, jornada_padrao - total_trabalhado)
            
            return pd.Series([total_trabalhado, extras, faltas])
        except:
            return pd.Series([0, 0, 0])

    df[['Trabalhado', 'Extras', 'Faltas']] = df.apply(calcular_jornada_completa, axis=1)

    # 5. Adicionar Totais ao final (substitua o bloco anterior por este)
    
    # Criamos uma linha de totais apenas com os valores numéricos
    row_totais = {
        'usuario__username': 'TOTAL',
        'Trabalhado': df['Trabalhado'].sum(),
        'Extras': df['Extras'].sum(),
        'Faltas': df['Faltas'].sum()
    }
    
    # Adicionamos essa linha ao DataFrame usando pd.concat
    df = pd.concat([df, pd.DataFrame([row_totais])], ignore_index=True)

    # 6. Exportação (Excel)
    nome_relatorio = f'relatorio_ponto_{datetime.now():%Y%m%d_%H%M%S}.xlsx'
    caminho_relatorio = os.path.join(settings.PONTO_DIR, nome_relatorio)
    with pd.ExcelWriter(caminho_relatorio, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    logger.info('Relatório de ponto gerado: %s por usuário %s', nome_relatorio, request.user.username)

    with open(caminho_relatorio, 'rb') as arquivo:
        response = HttpResponse(
            arquivo.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    response['Content-Disposition'] = f'attachment; filename="{nome_relatorio}"'
    return response

@login_required
def meu_perfil(request):
    # Tenta buscar ou cria o perfil se não existir
    perfil, created = PerfilFuncionario.objects.get_or_create(user=request.user)

    contracheques = Contracheque.objects.filter(usuario=request.user).order_by('-ano', '-mes')
    
    if request.method == 'POST':
        form = PerfilCompletoForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('meu_perfil')
    else:
        form = PerfilCompletoForm(instance=perfil)

    return render(request, 'ponto/perfil.html', {
        'perfil': perfil, 
        'contracheques': contracheques
    })

@login_required
def meu_historico(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    registros = RegistroPonto.objects.filter(usuario=request.user).order_by('-data_hora')
    
    # Aplica filtros se as datas forem fornecidas
    if data_inicio:
        registros = registros.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        registros = registros.filter(data_hora__date__lte=data_fim)
        
    # Paginação: 20 por página
    paginator = Paginator(registros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'ponto/historico.html', {
        'page_obj': page_obj, 
        'data_inicio': data_inicio, 
        'data_fim': data_fim
    })

@user_passes_test(is_ponto_rh, login_url='inicio')
def painel_rh(request):
    # Busca todos os pontos, ordenados pelos mais recentes
    registros = RegistroPonto.objects.all().order_by('-data_hora')
        
    context = {
        'registros': registros,
        'usuarios': User.objects.filter(is_active=True).only('username').order_by('username')
    }

    return render(request, 'ponto/painel_rh.html', context)

@user_passes_test(is_ponto_rh, login_url='inicio')
def editar_ponto(request, id):
    # Garante que o objeto existe
    registro = get_object_or_404(RegistroPonto, id=id)
    
    if request.method == 'POST':
        form = RegistroPontoForm(request.POST, instance=registro)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro editado com sucesso!")
            return redirect('painel_rh')
    else:
        form = RegistroPontoForm(instance=registro)
    
    return render(request, 'ponto/editar_ponto.html', {'form': form, 'registro': registro})

@user_passes_test(is_ponto_rh, login_url='inicio')
def editar_horario(request, user_id):
    perfil = get_object_or_404(PerfilFuncionario, user_id=user_id)
    
    if request.method == 'POST':
        form = PerfilCompletoForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('lista_funcionarios') # Ou para onde quiser voltar
    else:
        form = PerfilCompletoForm(instance=perfil)
        
    return render(request, 'ponto/editar_horario.html', {'form': form, 'perfil': perfil})

@user_passes_test(is_ponto_rh, login_url='inicio')
def apagar_ponto(request, ponto_id):
    # Busca o registro ou retorna erro 404 se não existir
    registro = get_object_or_404(RegistroPonto, id=ponto_id)
    
    # Deleta o registro
    registro.delete()
    
    messages.success(request, "Registro apagado com sucesso!", extra_tags='apagarponto')
    
    # Redireciona de volta para o painel do RH
    return redirect('painel_rh')

@user_passes_test(is_ponto_rh, login_url='inicio')
def registrar_ocorrencia(request):
    if request.method == 'POST':
        form = OcorrenciaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('painel_rh')
    else:
        form = OcorrenciaForm()
    return render(request, 'ponto/registrar_ocorrencia.html', {'form': form})

@user_passes_test(is_ponto_rh, login_url='inicio')
def listar_ocorrencias(request):
    ocorrencias = Ocorrencia.objects.all()
    # Formulário para criar (nova)
    form_novo = OcorrenciaForm()
    
    # Criamos uma lista de tuplas (ocorrencia, form_preenchido)
    lista_com_forms = []
    for o in ocorrencias:
        lista_com_forms.append((o, OcorrenciaForm(instance=o)))

    return render(request, 'ponto/listar_ocorrencias.html', {
        'lista_com_forms': lista_com_forms,
        'form': form_novo
    })

@user_passes_test(is_ponto_rh, login_url='inicio')
def editar_ocorrencia(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)
    if request.method == 'POST':
        form = OcorrenciaForm(request.POST, request.FILES, instance=ocorrencia)
        if form.is_valid():
            form.save()
            return redirect('listar_ocorrencias')
    else:
        form = OcorrenciaForm(instance=ocorrencia)
    return render(request, 'ponto/editar_ocorrencia.html', {'form': form})

@user_passes_test(is_ponto_rh, login_url='inicio')
def lista_funcionarios(request):
    # Aqui usamos .all() para buscar todos os perfis
    funcionarios = PerfilFuncionario.objects.all()
    
    return render(request, 'ponto/lista_funcionarios.html', {
        'funcionarios': funcionarios
    })

@user_passes_test(is_ponto_rh, login_url='inicio')
def editar_funcionario_rh(request, user_id):
    if request.method == 'POST':
        user = User.objects.get(id=user_id)
        # Lógica para salvar nomes, CPF, etc.
        user.first_name = request.POST.get('first_name')
        user.save()
        messages.success(request, "Dados atualizados!")
    return redirect('lista_funcionarios')

@user_passes_test(is_ponto_rh, login_url='inicio')
def apagar_ocorrencia(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)
    ocorrencia.delete()
    messages.success(request, "Ocorrência excluída com sucesso!", extra_tags='apagarocorrencia')
    return redirect('listar_ocorrencias')

@user_passes_test(is_ponto_rh, login_url='inicio')
def dashboard_presenca(request):
    hoje = date.today()
    # Pega todos os registros de entrada de hoje
    presencas_hoje = RegistroPonto.objects.filter(data_hora__date=hoje, tipo='ENTRADA')
    
    return render(request, 'ponto/dashboard_presenca.html', {
        'presencas': presencas_hoje,
        'data_hoje': hoje
    })

@user_passes_test(is_ponto_rh, login_url='inicio')
def pagina_relatorio(request):
    # Busca todos os funcionários para o select
    funcionarios = User.objects.filter(is_active=True)
    
    return render(request, 'ponto/relatorio.html', {'funcionarios': funcionarios})

@user_passes_test(is_ponto_rh, login_url='inicio')
def upload_contracheque(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        arquivo = request.FILES.get('arquivo')
        mes = request.POST.get('mes')
        ano = request.POST.get('ano')
        
        user = User.objects.get(id=user_id)
        Contracheque.objects.create(usuario=user, arquivo=arquivo, mes=mes, ano=ano)
        
        messages.success(request, "Contracheque enviado!")
        return redirect('lista_funcionarios')
    return redirect('lista_funcionarios')

@user_passes_test(is_ponto_rh, login_url='inicio')
def excluir_contracheque(request, contracheque_id):
    contracheque = get_object_or_404(Contracheque, id=contracheque_id)
    contracheque.arquivo.delete()
    contracheque.delete()
    messages.success(request, "Contracheque removido com sucesso!")
    return redirect('lista_funcionarios')

def logout_view(request):
    logout(request)
    return redirect('login')