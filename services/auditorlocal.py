import sqlite3
import requests
import re
import json
import html # Para escapar/desescapar entidades HTML
import os

# Certifique-se de que os caminhos de importação estão corretos para a estrutura do seu projeto
from services.extrator import extrair_dados_transcricao # Usado para obter dados gerais do atendimento
from services.diretrizes import registrar_auditoria, buscar_agente_por_email # buscar_agente_por_email é nova aqui

DB_PATH = "database/diretrizes.db" # Confirme se este é o caminho correto
TOGETHER_API_KEY = "tgp_v1_T-MXgORSpaf-k-VtfjYX2rPh_B8-0XFMxw_igPS2Mvw" # Sua chave da API

# A função obter_diretrizes_atuais não é usada diretamente no prompt da IA neste fluxo,
# mas pode ser mantida se você a usa em outro lugar ou planeia usá-la.
def obter_diretrizes_atuais():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT texto FROM diretrizes ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "Diretrizes não encontradas."

# Decoradores de autenticação e autorização (do seu código original)
# from routes.auth import login_required, apenas_supervisor
# Se esta função for chamada diretamente de uma rota Flask, os decoradores são importantes.
# Se for chamada apenas por outra função Python (como em main.py), eles podem não ser necessários aqui,
# mas sim na rota que a chama. Vou mantê-los comentados por enquanto, pois a chamada principal vem de main.py.
# @login_required
# @apenas_supervisor
def analisar_atendimento(transcricao_completa, comentario_cliente_geral, 
                         segmento_auditado_linhas=None, 
                         email_agente_auditado=None, 
                         estrelas_agente_auditado=None):

    # Determina qual texto de transcrição usar no prompt para a IA
    if segmento_auditado_linhas and email_agente_auditado:
        # Se estamos a auditar um segmento específico de um agente
        transcricao_para_prompt_ia = "\n".join(segmento_auditado_linhas)
        info_contexto_agente_prompt = f"do agente {email_agente_auditado}"
    else:
        # Se não for auditoria de segmento, usa a transcrição completa
        transcricao_para_prompt_ia = transcricao_completa
        # Tenta pegar o primeiro agente da transcrição completa para o texto do prompt
        temp_info_geral_prompt = extrair_dados_transcricao(transcricao_completa) 
        email_agente_geral_prompt = temp_info_geral_prompt.get('email_agente', 'desconhecido')
        info_contexto_agente_prompt = f"do agente {email_agente_geral_prompt} (análise geral)"

    # Validação básica
    if not transcricao_para_prompt_ia:
        return {
            "status": "erro", "parecer": "Erro",
            "justificativa": "Transcrição (ou segmento do agente) para análise está ausente.",
            "detalhes": None, "id_auditoria": None
        }
    
    comentario_cliente_para_prompt = comentario_cliente_geral if comentario_cliente_geral else "O cliente não deixou comentário."

    # Informação sobre as estrelas para adicionar ao prompt
    info_estrelas_prompt = ""
    if estrelas_agente_auditado is not None and email_agente_auditado: # Apenas se for auditoria de agente específico
        info_estrelas_prompt = f"- Este agente ({email_agente_auditado}) recebeu: {estrelas_agente_auditado} estrelas do cliente."

    # ----- ATUALIZE O PROMPT ABAIXO COM AS MELHORIAS DISCUTIDAS -----
    # 1. Parecer para elogio: "Comentário positivo confirmado"
    # 2. Pesos corretos nos critérios (ex: Postura e Solução peso 4, Conduta Geral peso 4)
    # 3. Nome do critério 7 como "Conduta Geral"
    # 4. Remoção de "pontuacao_final" do JSON que a IA deve gerar
    # 5. Exemplo de JSON mais completo e claro
    # O prompt abaixo é uma SUGESTÃO ATUALIZADA. Revise e ajuste conforme suas diretrizes finais.
    prompt = f"""
Você é o sistema audit.AI, responsável por analisar o desempenho de agentes em conversas de atendimento ao cliente.

Analise o seguinte TRECHO DA TRANSCRIÇÃO, que se refere à participação {info_contexto_agente_prompt}.

{info_estrelas_prompt}

O seguinte comentário GERAL foi feito pelo cliente sobre todo o atendimento (use-o para entender o contexto, mas foque sua análise no desempenho específico deste agente no trecho de transcrição fornecido):
"{html.escape(comentario_cliente_para_prompt)}"

Com base no trecho da transcrição do agente, no comentário geral do cliente e nas estrelas (se fornecidas para este agente), determine se a avaliação da atuação DESTE AGENTE é um ELOGIO ou uma RECLAMAÇÃO.

- Se a avaliação deste agente for um elogio e o agente agiu corretamente em seu segmento, o parecer sobre a atuação DESTE AGENTE deve ser "Comentário positivo confirmado".
- Se a avaliação deste agente indicar uma reclamação sobre sua atuação, avalie com base nas diretrizes abaixo se a reclamação é PROCEDENTE ou IMPROCEDENTE.

⚠️ Ao elaborar o RESUMO e a JUSTIFICATIVA FINAL (referentes à atuação DESTE AGENTE):
- NÃO use a palavra "reclamação" se o cliente elogiou este agente ou se o contexto geral aponta para satisfação com este agente.
- Use "manifestação positiva" ou "elogio" nesses casos.

---

📋 DIRETRIZES E PESOS (para avaliar a atuação DESTE AGENTE em seu segmento):

1. Tempo de Resposta (peso 1):
   - O agente deve responder em até 4 minutos entre interações.
   - Exceções: acesso remoto, pausas curtas (café, almoço) ou aviso de verificação.

2. Linguagem e Comunicação (peso 2):
   - Linguagem cordial, educada e objetiva.
   - Erros: uso de CAPS LOCK, gírias, palavras como "ué", "sei lá", etc.
   - A palavra "Citação:" em atendimentos, é uma resposta a uma mensagem especifica do cliente. Não deve ser considerada como falha ou problema no atendimento.
   - Links de ajuda https://ajuda.alterdata.com.br/ não devem ser considerados como falha ou problema no atendimento.
   
3. Postura e Solução (peso 3): - O agente deve fornecer uma solução real ou encaminhamento viável.
   - Evitar respostas vagas ("não tem o que fazer"), ausência de explicação ou demonstração de insegurança.

4. Empatia e Clareza (peso 3):
   - Demonstrar entendimento do problema.
   - Explicar com clareza e confirmar se o cliente entendeu.

5. Encerramento e Conduta Final (peso 3): - Nunca encerrar abruptamente ou sem perguntar se o cliente precisa de algo mais.
   - Se o cliente encerrou por inatividade, isso não é falha do agente.
   - Mensagens automáticas de encerramento por inatividade do cliente não são falha do agente.
   - Nenhum agente consegue encerrar o atendimento, portanto todo encerramento acontece porque o cliente encerrou ou houve problema com a conexão.

6. Procedimentos Técnicos e Segurança (peso 5):
   - Proibido usar comandos perigosos (DELETE, DROP, UPDATE sensível).
   - O agente deve ter conhecimento básico das funções no link: https://ajuda.alterdata.com.br/suporteexpress

7. Conduta Geral (peso 4): - Este critério avalia comportamentos falhos gerais não cobertos anteriormente.
   - Responder com uma única palavra ("sim", "ok") sem contexto.
   - Ignorar perguntas do cliente, demonstrar desinteresse, transferir sem justificar.

---

📞 Trecho da Transcrição {info_contexto_agente_prompt}:
{html.escape(transcricao_para_prompt_ia)}

---

🎯 Sua resposta deve conter exatamente o seguinte formato JSON (sem quebras de linha adicionais) referente à análise da atuação DESTE AGENTE:

{{
  "tipo_manifestacao": "elogio OU reclamacao",
  "resumo": "breve resumo da situação referente a este agente",
  "avaliacoes": [
    {{ "criterio": "Tempo de Resposta", "nota": 0-10, "justificativa": "justificativa" }},
    {{ "criterio": "Linguagem", "nota": 0-10, "justificativa": "justificativa" }},
    {{ "criterio": "Postura e Solução", "nota": 0-10, "justificativa": "justificativa" }},
    {{ "criterio": "Empatia e Clareza", "nota": 0-10, "justificativa": "justificativa" }},
    {{ "criterio": "Encerramento", "nota": 0-10, "justificativa": "justificativa (se aplicável ao segmento)" }},
    {{ "criterio": "Procedimentos Técnicos", "nota": 0-10, "justificativa": "justificativa" }},
    {{ "criterio": "Conduta Geral", "nota": 0-10, "justificativa": "justificativa" }}
  ],
  "parecer": "Comentário positivo confirmado OU PROCEDENTE OU IMPROCEDENTE",
  "justificativa_final": "explique claramente o porquê do parecer sobre este agente"
}}

Exemplo de estrutura para 'avaliacoes' e 'parecer':
{{
  "tipo_manifestacao": "reclamacao",
  "resumo": "Durante sua participação, o agente demonstrou demora na resposta inicial.",
  "avaliacoes": [
    {{ "criterio": "Tempo de Resposta", "nota": 3, "justificativa": "Demora excessiva na primeira resposta do agente neste segmento." }},
    {{ "criterio": "Linguagem", "nota": 9, "justificativa": "Comunicação clara e cordial." }}
  ],
  "parecer": "PROCEDENTE",
  "justificativa_final": "A atuação deste agente é considerada procedente em parte devido ao impacto negativo do tempo de resposta em seu turno."
}}

Responda sempre em português e no formato JSON acima.
"""

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1", # Confirme o modelo
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500, # Aumentado um pouco para JSONs mais complexos
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }

    id_auditoria_registrada = None # Para guardar o ID da auditoria após o registro

    try:
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status() # Levanta um erro para códigos de status HTTP 4xx/5xx

        json_data_resposta_ia = response.json()
        choices = json_data_resposta_ia.get("choices", [])

        if not (choices and "message" in choices[0] and "content" in choices[0]["message"]):
            raise ValueError("Resposta da IA não contém o conteúdo esperado.")

        conteudo_json_ia_str = choices[0]["message"]["content"].strip()
        
        # Tenta encontrar o JSON dentro da string, caso haja texto extra
        match_json = re.search(r'\{.*\}', conteudo_json_ia_str, re.DOTALL)
        if match_json:
            conteudo_json_ia_str = match_json.group(0)
        
        dados_ia = json.loads(conteudo_json_ia_str)
        
        tipo_manifestacao_ia = dados_ia.get("tipo_manifestacao", "").lower()
        avaliacoes_ia = dados_ia.get("avaliacoes", [])
        
        # Mapeamento dos nomes dos critérios da IA para as colunas do DB
        # Certifique-se que os nomes aqui ("Tempo de Resposta", etc.) são os mesmos que a IA retorna no JSON
        mapeamento_criterios_db = {
            "Tempo de Resposta": "nota_tempo_resposta",
            "Linguagem": "nota_linguagem",
            "Postura e Solução": "nota_postura_solucao",
            "Empatia e Clareza": "nota_empatia_clareza",
            "Encerramento": "nota_encerramento",
            "Procedimentos Técnicos": "nota_proced_tecnicos",
            "Conduta Geral": "nota_comport_falhos"
        }
        notas_criterios_para_db = {col: None for col in mapeamento_criterios_db.values()}

        for aval_item in avaliacoes_ia:
            criterio_nome_ia = aval_item.get("criterio")
            nota_valor_ia = aval_item.get("nota")
            if criterio_nome_ia in mapeamento_criterios_db and isinstance(nota_valor_ia, (int, float)):
                coluna_no_db = mapeamento_criterios_db[criterio_nome_ia]
                notas_criterios_para_db[coluna_no_db] = nota_valor_ia

        # Pesos para cálculo da nota final (DEVEM SER OS MESMOS DO PROMPT!)
        pesos_calculo = {
            "Tempo de Resposta": 1,
            "Linguagem": 2,
            "Postura e Solução": 3,
            "Empatia e Clareza": 3,
            "Encerramento": 3,
            "Procedimentos Técnicos": 5,
            "Conduta Geral": 4 
        }
        soma_ponderada_notas = 0
        soma_total_pesos = 0

        for aval_item in avaliacoes_ia: # Itera sobre as avaliações retornadas pela IA
            criterio_nome = aval_item.get("criterio")
            nota_valor = aval_item.get("nota", 0) # Default para 0 se a nota não vier
            if criterio_nome in pesos_calculo: # Só considera critérios com peso definido
                peso_do_criterio = pesos_calculo[criterio_nome]
                soma_ponderada_notas += nota_valor * peso_do_criterio
                soma_total_pesos += peso_do_criterio
        
        nota_final_calculada = round(soma_ponderada_notas / soma_total_pesos, 2) if soma_total_pesos > 0 else 0

        # Determinação do parecer final com base na nota calculada
        if nota_final_calculada >= 9 and (tipo_manifestacao_ia == "elogio" or estrelas_agente_auditado is not None and estrelas_agente_auditado >=4) : # Ajuste a condição de elogio
            parecer_final_sistema = "Comentário positivo confirmado"
        elif nota_final_calculada >= 7:
            parecer_final_sistema = "Improcedente"
        else:
            parecer_final_sistema = "Procedente"
        
        # O parecer da IA é uma sugestão, mas o parecer_final_sistema (baseado na nota) pode prevalecer.
        # Ou você pode usar o parecer da IA diretamente se confiar mais nele.
        # Aqui, vamos usar o parecer_final_sistema.
        dados_ia["parecer"] = parecer_final_sistema
        dados_ia["pontuacao_final"] = nota_final_calculada # Adiciona a nota calculada ao dict da IA

        # Coleta de informações gerais do atendimento e específicas do agente auditado
        info_geral_atendimento = extrair_dados_transcricao(transcricao_completa)
        
        agente_nome_para_registro = info_geral_atendimento.get("nome_agente", "Não identificado")
        agente_email_para_registro = info_geral_atendimento.get("email_agente", "Não identificado")
        equipe_para_registro = info_geral_atendimento.get("equipe", "Não cadastrada")
        supervisor_para_registro = info_geral_atendimento.get("supervisor", "Não cadastrado")
        responsavel_para_registro = info_geral_atendimento.get("responsavel_final_email", email_agente_auditado) # Default para o auditado

        if email_agente_auditado: # Se estamos auditando um agente específico
            info_agente_db = buscar_agente_por_email(email_agente_auditado)
            if info_agente_db:
                agente_nome_para_registro = info_agente_db.get("nome", email_agente_auditado.split('@')[0])
                agente_email_para_registro = email_agente_auditado
                equipe_para_registro = info_agente_db.get("equipe", "Não cadastrada")
                supervisor_para_registro = info_agente_db.get("supervisor", "Não cadastrado")
            else: # Fallback se agente não está no DB
                agente_nome_para_registro = email_agente_auditado.split('@')[0]
                agente_email_para_registro = email_agente_auditado
            responsavel_para_registro = email_agente_auditado # O agente auditado é o responsável pela sua parte

        id_auditoria_registrada = registrar_auditoria(
            agente_nome=agente_nome_para_registro,
            agente_email=agente_email_para_registro,
            equipe=equipe_para_registro,
            supervisor=supervisor_para_registro,
            numero_atendimento=info_geral_atendimento.get("numero_atendimento"),
            codigo_cliente=info_geral_atendimento.get("codigo_cliente"),
            parecer=parecer_final_sistema, # Usa o parecer calculado pelo sistema
            justificativa=dados_ia.get("justificativa_final", ""),
            tempo_total=info_geral_atendimento.get("tempo_total"), # Tempo total do atendimento geral
            tempo_medio_resposta=info_geral_atendimento.get("tempo_medio_resposta"), # TMR geral
            responsavel=responsavel_para_registro, 
            nota=nota_final_calculada, # Usa a nota calculada
            resumo=dados_ia.get("resumo", ""),
            avaliacoes_json=avaliacoes_ia, # Avaliações detalhadas da IA
            comentario_cliente=comentario_cliente_geral,
            # Passa as notas individuais dos critérios para o DB
            nota_tempo_resposta=notas_criterios_para_db.get("nota_tempo_resposta"),
            nota_linguagem=notas_criterios_para_db.get("nota_linguagem"),
            nota_postura_solucao=notas_criterios_para_db.get("nota_postura_solucao"),
            nota_empatia_clareza=notas_criterios_para_db.get("nota_empatia_clareza"),
            nota_encerramento=notas_criterios_para_db.get("nota_encerramento"),
            nota_proced_tecnicos=notas_criterios_para_db.get("nota_proced_tecnicos"),
            nota_comport_falhos=notas_criterios_para_db.get("nota_comport_falhos"),
            # Novos campos potenciais para o DB (se você os adicionar à tabela 'auditorias')
            # email_agente_avaliado=email_agente_auditado, # Para saber qual agente específico foi auditado
            # estrelas_recebidas=estrelas_agente_auditado # Estrelas que este agente recebeu
        )
        
        return {
            "status": "sucesso",
            "parecer": parecer_final_sistema,
            "justificativa": dados_ia.get("justificativa_final", ""),
            "detalhes": {
                "tipo_manifestacao": tipo_manifestacao_ia,
                "resumo": dados_ia.get("resumo", ""),
                "avaliacoes": avaliacoes_ia,
                "pontuacao_final": nota_final_calculada, # Envia a nota calculada
                "resposta_completa_ia": json_data_resposta_ia # Para debug ou referência
            },
            "id_auditoria": id_auditoria_registrada # Retorna o ID da auditoria registrada
        }

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão com a API Together AI: {str(e)}")
        return {"status": "erro", "parecer": "Erro API", "justificativa": f"Erro de comunicação com a IA: {str(e)}", "detalhes": None, "id_auditoria": None}
    except ValueError as e: # Erro ao fazer parse do JSON ou estrutura inesperada
        print(f"❌ Erro ao processar resposta da IA (ValueError): {str(e)}")
        print(f"Conteúdo problemático da IA: {conteudo_json_ia_str if 'conteudo_json_ia_str' in locals() else 'Não disponível'}")
        return {"status": "erro", "parecer": "Erro IA", "justificativa": f"Resposta da IA inválida ou mal formatada: {str(e)}", "detalhes": None, "id_auditoria": None}
    except Exception as e:
        import traceback
        print(f"❌ Erro inesperado na análise de atendimento: {str(e)}")
        print(traceback.format_exc()) # Imprime o stack trace completo para depuração
        return {"status": "erro", "parecer": "Erro Interno", "justificativa": f"Ocorreu um erro interno no sistema: {str(e)}", "detalhes": None, "id_auditoria": None}


def gerar_feedback(parecer, justificativa, detalhes=None):
    # Esta função permanece como no seu código original, pois ela formata o feedback para exibição.
    # Certifique-se que ela lida bem com 'detalhes' que agora contêm 'pontuacao_final' calculada.
    if not detalhes:
        return "<p>Sem justificativa ou detalhes para exibir.</p>"

    resumo = html.escape(detalhes.get("resumo", "-"))
    avaliacoes = detalhes.get("avaliacoes", [])
    nota_final = detalhes.get("pontuacao_final", "-") # Já é a nota calculada

    feedback_html_str = f"<p><strong>Resumo da Análise:</strong> {resumo}</p>"

    if avaliacoes:
        feedback_html_str += """
        <table class="feedback-table">
            <thead>
                <tr>
                    <th>Critério Avaliado</th>
                    <th>Nota Atribuída</th>
                    <th>Justificativa da IA</th>
                </tr>
            </thead>
            <tbody>
        """
        for item_aval in avaliacoes:
            criterio = html.escape(item_aval.get("criterio", "-"))
            nota = html.escape(str(item_aval.get("nota", "-")))
            motivo = html.escape(item_aval.get("justificativa", "-"))
            feedback_html_str += f"""
                <tr>
                    <td>{criterio}</td>
                    <td>{nota}</td>
                    <td>{motivo}</td>
                </tr>
            """
        feedback_html_str += "</tbody></table>"
    else:
        feedback_html_str += "<p>Nenhuma avaliação detalhada por critério foi fornecida pela IA.</p>"


    if isinstance(nota_final, (float, int)):
        cor_nota_css = "green" if nota_final >= 7 else ("orange" if nota_final >= 5 else "red") # Exemplo de mais cores
        feedback_html_str += f"<p style='margin-top:1rem;'><strong>Pontuação Final Calculada:</strong> <span style='color:{cor_nota_css};font-weight:bold;font-size:1.2rem'>{nota_final}</span></p>"
    else:
        feedback_html_str += "<p><strong>Pontuação Final Calculada:</strong> -</p>"

    if parecer == "Procedente":
        frase_conclusao = "A reclamação sobre a atuação do agente foi considerada procedente."
    elif parecer == "Improcedente":
        frase_conclusao = "A reclamação sobre a atuação do agente foi considerada improcedente."
    elif parecer == "Comentário positivo confirmado":
        frase_conclusao = "A manifestação positiva sobre a atuação do agente foi confirmada."
    else:
        frase_conclusao = "A análise da atuação do agente não foi conclusiva ou o parecer é 'Outro'."

    feedback_html_str += f"<p class='conclusao' style='margin-top:1rem;'><strong>Conclusão do Sistema: {html.escape(parecer)}</strong></p>"
    feedback_html_str += f"<p class='conclusao'><em>{frase_conclusao}</em></p>"
    if justificativa: # Justificativa final da IA
        feedback_html_str += f"<p class='conclusao'><strong>Justificativa da IA:</strong> {html.escape(justificativa)}</p>"

    return feedback_html_str


def gerar_feedback(parecer, justificativa, detalhes=None):
    if not detalhes:
        return "<p>Sem justificativa..</p>"

    resumo = detalhes.get("resumo", "-")
    avaliacoes = detalhes.get("avaliacoes", [])
    nota_final = detalhes.get("pontuacao_final", "-")

    html = f"<p><strong>Resumo:</strong> {resumo}</p>"

    html += """
    <table class="feedback-table">
        <thead>
            <tr>
                <th>Categoria</th>
                <th>Nota</th>
                <th>Justificativa</th>
            </tr>
        </thead>
        <tbody>
    """

    for item in avaliacoes:
        criterio = item.get("criterio", "-")
        nota = item.get("nota", "-")
        motivo = item.get("justificativa", "-")
        html += f"""
            <tr>
                <td>{criterio}</td>
                <td>{nota}</td>
                <td>{motivo}</td>
            </tr>
        """

    html += "</tbody></table>"

    if isinstance(nota_final, (float, int)):
        cor_nota = "green" if nota_final >= 7 else "red"
        html += f"<p style='margin-top:1rem;'><strong>Pontuação Final:</strong> <span style='color:{cor_nota};font-weight:bold;font-size:1.2rem'>{nota_final}</span></p>"
    else:
        html += "<p><strong>Pontuação Final:</strong> -</p>"

    # Conclusão correta e concisa
    if parecer == "Procedente":
        frase_base = "A reclamação do cliente foi considerada procedente."
    elif parecer == "Improcedente":
        frase_base = "A reclamação do cliente foi considerada improcedente."
    elif parecer == "Comentário positivo confirmado":
        frase_base = "O elogio do cliente foi confirmado como positivo."
    else:
        frase_base = "A análise não foi conclusiva."

    html += f"<p class='conclusao'><strong>{frase_base}</strong></p>"
    html += f"<p class='conclusao'>{justificativa}</p>"

    return html
