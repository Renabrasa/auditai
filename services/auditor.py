# services/auditor.py

# --- IMPORTS NECESSÁRIOS ---
import requests
import re
import json
import html
import os
import traceback # Para depuração de erros completos

# Ajuste os caminhos de importação conforme a estrutura do seu projeto
from services.extrator import extrair_dados_transcricao, segmentar_transcricao
from services.diretrizes import registrar_auditoria, buscar_agente_por_email

# Importar o modelo Auditoria para buscar o último ID (se necessário)
from database import db # Para acessar o objeto db do SQLAlchemy
from models import Auditoria # Para interagir com a tabela de auditorias

# As rotas de autenticação/autorização são geralmente aplicadas diretamente nas rotas Flask,
# não nas funções de serviço. Se precisar, pode importá-los, mas removidos daqui para clareza.
# from routes.auth import login_required, apenas_supervisor


def analisar_atendimento(transcricao_completa: str, comentario_cliente_geral: str,
                         segmento_auditado_linhas: list = None,
                         email_agente_auditado: str = None,
                         estrelas_agente_auditado: int = None) -> dict:
    """
    Analisa um atendimento ou um segmento específico de um atendimento usando a IA
    e registra a auditoria no banco de dados.

    Args:
        transcricao_completa: A transcrição completa do atendimento.
        comentario_cliente_geral: O comentário geral do cliente sobre o atendimento.
        segmento_auditado_linhas: Lista de linhas da transcrição se for um segmento específico.
        email_agente_auditado: Email do agente cujo segmento está sendo auditado.
        estrelas_agente_auditado: Número de estrelas dadas pelo cliente ao agente (se aplicável).

    Returns:
        Um dicionário com o status da análise, parecer, justificativa, detalhes e ID da auditoria.
    """

    # --- CONFIGURAÇÃO DA API KEY (Lida no momento da execução da função) ---
    # A chave da API deve ser lida de uma variável de ambiente para segurança em produção.
    TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
    if not TOGETHER_API_KEY:
        # Se a chave não for encontrada, retorna um erro para a rota chamadora.
        return {
            "status": "erro", "parecer": "Erro Interno",
            "justificativa": "TOGETHER_API_KEY não configurada. Contate o administrador do sistema.",
            "detalhes": None, "id_auditoria": None
        }
    # --- FIM DA CONFIGURAÇÃO DA API KEY ---


    # 1. Determina qual texto de transcrição usar no prompt para a IA
    transcricao_para_prompt_ia = ""
    info_contexto_agente_prompt = ""

    if segmento_auditado_linhas and email_agente_auditado:
        # Auditoria de um segmento específico de um agente
        transcricao_para_prompt_ia = "\n".join(segmento_auditado_linhas)
        info_contexto_agente_prompt = f"da participação do agente {email_agente_auditado}"
    else:
        # Auditoria da transcrição completa
        transcricao_para_prompt_ia = transcricao_completa
        # Tenta pegar o primeiro agente da transcrição completa para o texto do prompt
        temp_info_geral_prompt = extrair_dados_transcricao(transcricao_completa)
        email_agente_geral_prompt = temp_info_geral_prompt.get('email_agente', 'não identificado')
        info_contexto_agente_prompt = f"do atendimento geral (agente principal: {email_agente_geral_prompt})"

    # Validação básica de entrada
    if not transcricao_para_prompt_ia:
        return {
            "status": "erro", "parecer": "Erro",
            "justificativa": "Transcrição (ou segmento do agente) para análise está ausente.",
            "detalhes": None, "id_auditoria": None
        }

    comentario_cliente_para_prompt = comentario_cliente_geral.strip() if comentario_cliente_geral else "O cliente não deixou comentário."

    # Informação sobre as estrelas para adicionar ao prompt
    info_estrelas_prompt = ""
    if estrelas_agente_auditado is not None and email_agente_auditado:
        info_estrelas_prompt = f"- Este agente ({email_agente_auditado}) recebeu: {estrelas_agente_auditado} estrelas do cliente."

    # 2. Construção do Prompt para a IA
    prompt = f"""
Você é o sistema audit.AI, responsável por analisar o desempenho de agentes em conversas de atendimento ao cliente.

Analise o seguinte TRECHO DA TRANSCRIÇÃO, que se refere à participação {info_contexto_agente_prompt}.

{info_estrelas_prompt}

O seguinte comentário GERAL foi feito pelo cliente sobre todo o atendimento (use-o para entender o contexto, mas foque sua análise no desempenho específico deste agente no trecho de transcrição fornecido):
"{html.escape(comentario_cliente_para_prompt)}"

Com base no trecho da transcrição do agente, no comentário geral do cliente e nas estrelas (se fornecidas para este agente), determine se a avaliação da atuação DESTE AGENTE é um ELOGIO ou uma RECLAMAÇÃO.

- Se a avaliação deste agente for um elogio e o agente agiu corretamente em seu segmento, o parecer sobre a atuação DESTE AGENTE deve ser "Comentário positivo confirmado".
- Se a avaliação deste agente indicar uma reclamação sobre sua atuação, avalie com base nas diretrizes abaixo se a reclamação é PROCEDENTE ou IMPROCEDENTE.

⚠️ Ao elaborar o RESUMO (referente à atuação DESTE AGENTE):
- Ele deve INCLUIR um breve resumo do PROBLEMA DO CLIENTE e, em seguida, um resumo da ANÁLISE ESPECÍFICA da atuação DESTE AGENTE.
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

3. Postura e Solução (peso 3):
   - O agente deve fornecer uma solução real ou encaminhamento viável.
   - Evitar respostas vagas ("não tem o que fazer"), ausência de explicação ou demonstração de insegurança.

4. Empatia e Clareza (peso 3):
   - Demonstrar entendimento do problema.
   - Explicar com clareza e confirmar se o cliente entendeu.

5. Encerramento e Conduta Final (peso 3):
   - Nunca encerrar abruptamente ou sem perguntar se o cliente precisa de algo mais.
   - Se o cliente encerrou por inatividade, isso não é falha do agente.
   - Mensagens automáticas de encerramento por inatividade do cliente não são falha do agente.
   - Nenhum agente consegue encerrar o atendimento, portanto todo encerramento acontece porque o cliente encerrou ou houve problema com a conexão.

6. Procedimentos Técnicos e Segurança (peso 5):
   - Proibido usar comandos perigosos (DELETE, DROP, UPDATE sensível).
   - O agente deve ter conhecimento básico das funções no link: https://ajuda.alterdata.com.br/suporteexpress

7. Conduta Geral (peso 4):
   - Este critério avalia comportamentos falhos gerais não cobertos anteriormente.
   - Responder com uma única palavra ("sim", "ok") sem contexto.
   - Ignorar perguntas do cliente, demonstrar desinteresse, transferir sem justificar.

---

📞 Trecho da Transcrição {info_contexto_agente_prompt}:
{html.escape(transcricao_para_prompt_ia)}

---

🎯 Sua resposta deve conter exatamente o seguinte formato JSON (sem quebras de linha adicionais) referente à análise da atuação DESTE AGENTE:

{{
  "tipo_manifestacao": "elogio OU reclamacao",
  "resumo": "Um breve resumo do problema do cliente e da situação referente a este agente.",
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

    # 3. Cabeçalhos e Payload para a Requisição da API Together AI
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1", # Modelo da IA. Confirme se é o desejado.
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500, # Aumentado para acomodar JSONs mais complexos
        "temperature": 0.4, # Ajuste a temperatura para menos criatividade e mais consistência
        "response_format": {"type": "json_object"} # Solicita resposta em JSON
    }

    id_auditoria_registrada = None # Variável para guardar o ID da auditoria após o registro

    try:
        # 4. Envia a Requisição para a API da Together AI
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status() # Levanta um erro para códigos de status HTTP 4xx/5xx

        json_data_resposta_ia = response.json()
        choices = json_data_resposta_ia.get("choices", [])

        # 5. Processa a Resposta da IA
        if not (choices and "message" in choices[0] and "content" in choices[0]["message"]):
            raise ValueError("Resposta da IA não contém o conteúdo esperado (choices, message ou content ausentes).")

        conteudo_json_ia_str = choices[0]["message"]["content"].strip()

        # Tenta encontrar o JSON dentro da string, caso a IA adicione texto extra
        match_json = re.search(r'\{.*\}', conteudo_json_ia_str, re.DOTALL)
        if match_json:
            conteudo_json_ia_str = match_json.group(0)
        else:
            raise ValueError("Não foi possível extrair um objeto JSON válido da resposta da IA.")

        dados_ia = json.loads(conteudo_json_ia_str)

        tipo_manifestacao_ia = dados_ia.get("tipo_manifestacao", "").lower()
        avaliacoes_ia = dados_ia.get("avaliacoes", [])

        # 6. Mapeamento e Coleta de Notas por Critério para o Banco de Dados
        # Certifique-se que os nomes dos critérios ("Tempo de Resposta", etc.) na IA
        # correspondem EXATAMENTE às chaves deste dicionário.
        mapeamento_criterios_db = {
            "Tempo de Resposta": "nota_tempo_resposta",
            "Linguagem": "nota_linguagem",
            "Postura e Solução": "nota_postura_solucao",
            "Empatia e Clareza": "nota_empatia_clareza",
            "Encerramento": "nota_encerramento",
            "Procedimentos Técnicos": "nota_proced_tecnicos",
            "Conduta Geral": "nota_comport_falhos" # Mapeia 'Conduta Geral' da IA para 'nota_comport_falhos' no DB
        }
        notas_criterios_para_db = {col: None for col in mapeamento_criterios_db.values()}

        for aval_item in avaliacoes_ia:
            criterio_nome_ia = aval_item.get("criterio")
            nota_valor_ia = aval_item.get("nota")
            if criterio_nome_ia in mapeamento_criterios_db and isinstance(nota_valor_ia, (int, float)):
                coluna_no_db = mapeamento_criterios_db[criterio_nome_ia]
                notas_criterios_para_db[coluna_no_db] = nota_valor_ia

        # 7. Cálculo da Nota Final Ponderada
        # Estes pesos DEVEM SER OS MESMOS QUE VOCÊ INFORMOU À IA NO PROMPT!
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

        for aval_item in avaliacoes_ia:
            criterio_nome = aval_item.get("criterio")
            nota_valor = aval_item.get("nota", 0) # Default para 0 se a nota não vier
            if criterio_nome in pesos_calculo:
                peso_do_criterio = pesos_calculo[criterio_nome]
                soma_ponderada_notas += nota_valor * peso_do_criterio
                soma_total_pesos += peso_do_criterio

        nota_final_calculada = round(soma_ponderada_notas / soma_total_pesos, 2) if soma_total_pesos > 0 else 0

        # 8. Determinação do Parecer Final do Sistema
        # Esta lógica define o parecer final com base na nota calculada e tipo de manifestação.
        if (nota_final_calculada >= 9 and tipo_manifestacao_ia == "elogio") or \
           (estrelas_agente_auditado is not None and estrelas_agente_auditado >= 4):
            parecer_final_sistema = "Comentário positivo confirmado"
        elif nota_final_calculada >= 7:
            parecer_final_sistema = "Improcedente"
        else:
            parecer_final_sistema = "Procedente"

        # Adiciona o parecer e a nota calculada ao dicionário de dados da IA para retorno
        dados_ia["parecer"] = parecer_final_sistema
        dados_ia["pontuacao_final"] = nota_final_calculada

        # 9. Coleta de Informações do Agente para Registro no Banco de Dados
        info_geral_atendimento = extrair_dados_transcricao(transcricao_completa)

        agente_nome_para_registro = info_geral_atendimento.get("nome_agente", "Não identificado")
        agente_email_para_registro = info_geral_atendimento.get("email_agente", "nao_identificado@exemplo.com")
        equipe_para_registro = info_geral_atendimento.get("equipe", "Não cadastrada")
        supervisor_para_registro = info_geral_atendimento.get("supervisor", "Não cadastrado")
        responsavel_para_registro = info_geral_atendimento.get("responsavel_final_email", email_agente_auditado)

        # Se for auditoria de um agente específico, tenta buscar informações do agente no DB
        if email_agente_auditado:
            info_agente_db = buscar_agente_por_email(email_agente_auditado) # Usa a função de diretrizes.py
            if info_agente_db:
                agente_nome_para_registro = info_agente_db.get("nome", email_agente_auditado.split('@')[0])
                agente_email_para_registro = email_agente_auditado # Garante que o email é o do agente auditado
                equipe_para_registro = info_agente_db.get("equipe", "Não cadastrada")
                supervisor_para_registro = info_agente_db.get("supervisor", "Não cadastrado")
            else: # Fallback se agente não está no DB de agentes
                agente_nome_para_registro = email_agente_auditado.split('@')[0]
                agente_email_para_registro = email_agente_auditado
            responsavel_para_registro = email_agente_auditado # O agente auditado é o responsável pela sua parte

        # 10. Registra a Auditoria no Banco de Dados (via services.diretrizes)
        registro_bem_sucedido = registrar_auditoria(
            agente_nome=agente_nome_para_registro,
            agente_email=agente_email_para_registro,
            equipe=equipe_para_registro,
            supervisor=supervisor_para_registro,
            numero_atendimento=info_geral_atendimento.get("numero_atendimento"),
            codigo_cliente=info_geral_atendimento.get("codigo_cliente"),
            parecer=parecer_final_sistema, # Usa o parecer calculado pelo sistema
            justificativa=dados_ia.get("justificativa_final", ""),
            tempo_total=info_geral_atendimento.get("tempo_total"),
            tempo_medio_resposta=info_geral_atendimento.get("tempo_medio_resposta"),
            responsavel=responsavel_para_registro,
            nota=nota_final_calculada,
            resumo=dados_ia.get("resumo", ""),
            avaliacoes_json=avaliacoes_ia,
            comentario_cliente=comentario_cliente_geral,
            nota_tempo_resposta=notas_criterios_para_db.get("nota_tempo_resposta"),
            nota_linguagem=notas_criterios_para_db.get("nota_linguagem"),
            nota_postura_solucao=notas_criterios_para_db.get("nota_postura_solucao"),
            nota_empatia_clareza=notas_criterios_para_db.get("nota_empatia_clareza"),
            nota_encerramento=notas_criterios_para_db.get("nota_encerramento"),
            nota_proced_tecnicos=notas_criterios_para_db.get("nota_proced_tecnicos"),
            nota_comport_falhos=notas_criterios_para_db.get("nota_comport_falhos")
        )

        # Se o registro no banco de dados falhou, retorna um status de erro
        if not registro_bem_sucedido:
            return {
                "status": "erro", "parecer": "Erro Interno",
                "justificativa": "Falha ao registrar a auditoria no banco de dados.",
                "detalhes": None, "id_auditoria": None
            }

        # 11. Obtém o ID da Auditoria Recém-Registrada
        # Isso é uma forma simples; em sistemas de alta concorrência, `registrar_auditoria`
        # deveria retornar o ID para ser 100% seguro.
        try:
            ultima_auditoria = Auditoria.query.order_by(Auditoria.data.desc()).first()
            if ultima_auditoria:
                id_auditoria_registrada = ultima_auditoria.id
        except Exception as e:
            print(f"AVISO: Não foi possível obter o ID da última auditoria registrada: {e}")
            id_auditoria_registrada = None # Continua, mas sem o ID

        # 12. Retorna o Resultado da Análise
        return {
            "status": "sucesso",
            "parecer": parecer_final_sistema,
            "justificativa": dados_ia.get("justificativa_final", ""),
            "detalhes": {
                "tipo_manifestacao": tipo_manifestacao_ia,
                "resumo": dados_ia.get("resumo", ""),
                "avaliacoes": avaliacoes_ia,
                "pontuacao_final": nota_final_calculada,
                "resposta_completa_ia": json_data_resposta_ia # Para debug ou referência
            },
            "id_auditoria": id_auditoria_registrada
        }

    # Tratamento de Exceções
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão/API com Together AI: {str(e)}")
        return {"status": "erro", "parecer": "Erro API", "justificativa": f"Erro de comunicação com a IA: {str(e)}", "detalhes": None, "id_auditoria": None}
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON da IA: {e}")
        print(f"Conteúdo que causou erro de JSON: '{conteudo_json_ia_str if 'conteudo_json_ia_str' in locals() else 'Não disponível'}'")
        return {"status": "erro", "parecer": "Erro IA", "justificativa": f"Resposta da IA não é um JSON válido: {str(e)}", "detalhes": None, "id_auditoria": None}
    except ValueError as e:
        print(f"❌ Erro ao processar resposta da IA (ValueError): {str(e)}")
        return {"status": "erro", "parecer": "Erro IA", "justificativa": f"Formato de resposta da IA inesperado: {str(e)}", "detalhes": None, "id_auditoria": None}
    except Exception as e:
        # Captura e imprime qualquer outro erro inesperado
        print(f"❌ Erro inesperado na análise de atendimento: {str(e)}")
        print(traceback.format_exc()) # Imprime o stack trace completo para depuração
        return {"status": "erro", "parecer": "Erro Interno", "justificativa": f"Ocorreu um erro interno no sistema: {str(e)}", "detalhes": None, "id_auditoria": None}