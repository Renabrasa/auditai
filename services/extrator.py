import re
from datetime import datetime, timedelta
# Certifique-se de que o 'services' está no caminho do Python ou ajuste o import
# Se diretrizes.py está na mesma pasta 'services', este import deve funcionar.
from services.diretrizes import buscar_agente_por_email

# NOVA FUNÇÃO PARA SEGMENTAR A TRANSCRIÇÃO
def segmentar_transcricao(transcricao_completa):
    linhas = transcricao_completa.strip().splitlines()
    segmentos = []
    segmento_atual_linhas = []
    agente_email_atual = None
    nome_agente_karoo_atual = None # Para guardar o nome que aparece em "Você está conversando com..."

    # Padrões Regex para identificar agentes e mensagens do sistema
    # Este padrão busca por "Agente atendendo email@infoalter.com.br" no início da linha (após espaços opcionais)
    padrao_agente_atendendo_linha = re.compile(r"^\s*Agente atendendo\s+([^@\s]+@infoalter\.com\.br)", re.IGNORECASE)
    # Este padrão busca por "system@karoo (...) Você está conversando com Nome do Agente."
    padrao_voce_conversando_com = re.compile(r"system@karoo .* Você está conversando com ([^.]+)\.", re.IGNORECASE)
    # Este padrão busca por "email@infoalter.com.br (dd/mm/aaaa hh:mm:ss):" no início da linha
    padrao_mensagem_agente_inicio_linha = re.compile(r"^([^@\s]+@infoalter\.com\.br)\s+\(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\):", re.IGNORECASE)

    def finalizar_segmento_anterior():
        nonlocal segmento_atual_linhas, agente_email_atual, nome_agente_karoo_atual
        if agente_email_atual and segmento_atual_linhas:
            segmentos.append({
                "agente_email": agente_email_atual,
                "nome_agente_karoo": nome_agente_karoo_atual,
                "linhas_segmento": list(segmento_atual_linhas) # Cria uma cópia
            })
            segmento_atual_linhas.clear()
        # nome_agente_karoo_atual será resetado ou definido quando um novo agente for identificado

    for linha in linhas:
        email_detectado_marcador_direto = None
        nome_detectado_karoo_na_linha = None
        
        match_agente_linha = padrao_agente_atendendo_linha.search(linha)
        if match_agente_linha:
            email_detectado_marcador_direto = match_agente_linha.group(1).lower()

        match_voce_conversando = padrao_voce_conversando_com.search(linha)
        if match_voce_conversando:
            nome_detectado_karoo_na_linha = match_voce_conversando.group(1).strip()

        # Prioridade 1: Marcador explícito "Agente atendendo [email]"
        if email_detectado_marcador_direto and email_detectado_marcador_direto != agente_email_atual:
            finalizar_segmento_anterior()
            agente_email_atual = email_detectado_marcador_direto
            nome_agente_karoo_atual = nome_detectado_karoo_na_linha # Se o nome veio na mesma linha ou contexto
            segmento_atual_linhas.append(linha) 
            continue

        # Se a linha é uma mensagem de agente (ex: "usuario@infoalter.com.br (data): msg")
        match_msg_agente = padrao_mensagem_agente_inicio_linha.match(linha)
        if match_msg_agente:
            email_da_mensagem = match_msg_agente.group(1).lower()
            if agente_email_atual is None: # Primeiro agente identificado
                agente_email_atual = email_da_mensagem
                # Se nome_detectado_karoo_na_linha foi pego antes (pouco provável sem email), associaria aqui
                if nome_detectado_karoo_na_linha and nome_agente_karoo_atual is None:
                    nome_agente_karoo_atual = nome_detectado_karoo_na_linha
            elif email_da_mensagem != agente_email_atual: # Mudança de agente inferida pelo prefixo
                finalizar_segmento_anterior()
                agente_email_atual = email_da_mensagem
                nome_agente_karoo_atual = None # Resetar, pois não temos o nome completo por esta via
        
        # Se uma linha "Você está conversando com [Nome]" aparece e o agente_email_atual já é conhecido,
        # apenas atualizamos o nome_agente_karoo_atual.
        if nome_detectado_karoo_na_linha and agente_email_atual is not None:
            # Idealmente, aqui você teria uma forma de verificar se 'nome_detectado_karoo_na_linha'
            # realmente corresponde ao 'agente_email_atual' (ex: consultando seu DB de agentes).
            # Por simplicidade, vamos apenas atualizar o nome se não tivermos um ainda para o agente atual,
            # ou se for um nome diferente para o mesmo agente (o que é menos comum).
            if nome_agente_karoo_atual is None or nome_agente_karoo_atual != nome_detectado_karoo_na_linha:
                 nome_agente_karoo_atual = nome_detectado_karoo_na_linha
        
        if agente_email_atual is not None:
            segmento_atual_linhas.append(linha)

    finalizar_segmento_anterior()
    return segmentos


def extrair_dados_transcricao(transcricao):
    linhas = transcricao.strip().splitlines()
    # Chamada para a nova função de segmentação
    segmentos = segmentar_transcricao(transcricao)

    numero_atendimento = "Não identificado"
    codigo_cliente = "Não identificado"
    timestamps_gerais = [] # Para calcular tempo total geral
    
    # Informações do primeiro agente para o resumo (ou o único, se não houver outros)
    email_primeiro_agente = None
    nome_primeiro_agente_display = "Não identificado"
    agente_info_primeiro_db = None
    
    # Lista de todos os participantes para exibição
    participantes_info = []
    # Email do último agente nos segmentos, para "responsavel_final_email"
    email_responsavel_extrator = "Não identificado"

    if segmentos:
        # Dados do primeiro agente (para manter a compatibilidade com o resumo atual)
        primeiro_segmento = segmentos[0]
        email_primeiro_agente = primeiro_segmento.get("agente_email")
        
        if email_primeiro_agente:
            agente_info_primeiro_db = buscar_agente_por_email(email_primeiro_agente)
            if agente_info_primeiro_db and agente_info_primeiro_db.get("nome"):
                nome_primeiro_agente_display = agente_info_primeiro_db.get("nome")
            elif primeiro_segmento.get("nome_agente_karoo"): # Nome detectado pela linha "Você está conversando com..."
                nome_primeiro_agente_display = primeiro_segmento.get("nome_agente_karoo")
            else: # Fallback se não tiver nome no DB nem nome Karoo, usa parte do email
                nome_primeiro_agente_display = email_primeiro_agente.split('@')[0]

        # Coletar informações de todos os participantes únicos
        emails_unicos_participantes = set()
        for seg in segmentos:
            email_p = seg.get("agente_email")
            if email_p and email_p not in emails_unicos_participantes:
                info_p_db = buscar_agente_por_email(email_p)
                nome_p_karoo = seg.get("nome_agente_karoo")
                
                nome_p_display_lista = email_p.split('@')[0] # Fallback inicial
                if info_p_db and info_p_db.get("nome"):
                    nome_p_display_lista = info_p_db.get("nome")
                elif nome_p_karoo: # Usa o nome Karoo se disponível e não tiver do DB
                    nome_p_display_lista = nome_p_karoo
                
                participantes_info.append({
                    "email": email_p,
                    "nome": nome_p_display_lista
                })
                emails_unicos_participantes.add(email_p)
        
        # Define o responsável final como o último agente que interagiu nos segmentos
        if segmentos[-1].get("agente_email"):
            email_responsavel_extrator = segmentos[-1].get("agente_email")
    else:
        # Se não houver segmentos (ex: transcrição vazia ou sem agentes identificáveis),
        # tenta pegar um email geral da transcrição como antes (lógica simplificada)
        emails_encontrados_geral = re.findall(r'[\w\.-]+@infoalter\.com\.br', transcricao, re.IGNORECASE)
        if emails_encontrados_geral:
            email_primeiro_agente = emails_encontrados_geral[0].lower() # Pega o primeiro email @infoalter encontrado
            agente_info_primeiro_db = buscar_agente_por_email(email_primeiro_agente)
            if agente_info_primeiro_db and agente_info_primeiro_db.get("nome"):
                nome_primeiro_agente_display = agente_info_primeiro_db.get("nome")
            else:
                nome_primeiro_agente_display = email_primeiro_agente.split('@')[0]
            email_responsavel_extrator = email_primeiro_agente


    # Extração de numero_atendimento e codigo_cliente (da sua lógica original)
    for linha_idx, linha_conteudo in enumerate(linhas[:10]):
        match_atendimento = re.search(r"ID do atendimento:\s*(\d+)", linha_conteudo, re.IGNORECASE)
        if match_atendimento:
            numero_atendimento = match_atendimento.group(1)

        match_cliente = re.search(r"Cliente de contato:\s*(\d{5,})", linha_conteudo, re.IGNORECASE)
        if match_cliente:
            codigo_cliente = match_cliente.group(1)
            
    # Extração de timestamps para cálculo de tempo total (da sua lógica original, adaptada)
    padrao_timestamp_completo = re.compile(r'\((\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\)')
    for linha_conteudo in linhas:
        match_ts = padrao_timestamp_completo.search(linha_conteudo)
        if match_ts:
            try:
                # Adiciona o objeto datetime diretamente
                timestamps_gerais.append(datetime.strptime(match_ts.group(1), "%d/%m/%Y %H:%M:%S"))
            except ValueError:
                pass # Ignora timestamps mal formatados

    hora_inicio_obj = None
    hora_fim_obj = None
    tempo_total_delta = None

    if timestamps_gerais:
        timestamps_gerais.sort() # Garante que estão em ordem
        hora_inicio_obj = timestamps_gerais[0]
        hora_fim_obj = timestamps_gerais[-1]
        if hora_fim_obj > hora_inicio_obj:
             tempo_total_delta = hora_fim_obj - hora_inicio_obj

    return {
        "nome_agente": nome_primeiro_agente_display, # Nome do primeiro agente (ou principal)
        "email_agente": email_primeiro_agente or "Não identificado", # Email do primeiro agente
        "hora_inicio": hora_inicio_obj.strftime("%d/%m/%Y %H:%M:%S") if hora_inicio_obj else "Não identificada",
        "tempo_total": str(tempo_total_delta).split(".")[0] if tempo_total_delta else "Não identificado",
        "tempo_medio_resposta": "N/A (geral)", # Este cálculo precisaria ser refeito para ser por agente ou mais preciso
        "equipe": agente_info_primeiro_db.get("equipe") if agente_info_primeiro_db else "Não cadastrada",
        "supervisor": agente_info_primeiro_db.get("supervisor") if agente_info_primeiro_db else "Não cadastrado",
        "numero_atendimento": numero_atendimento,
        "codigo_cliente": codigo_cliente,
        "responsavel_final_email": email_responsavel_extrator, 
        "participantes": participantes_info # <<< A NOVA LISTA DE TODOS OS AGENTES QUE PARTICIPARAM
    }