from flask import Blueprint, render_template
import sqlite3
import json
from routes.auth import login_required, apenas_supervisor


bp = Blueprint('dashboard', __name__, url_prefix="/dashboard")

def get_conexao():
    return sqlite3.connect("database/diretrizes.db")

from flask import Blueprint, render_template
import sqlite3
import json

bp = Blueprint('dashboard', __name__, url_prefix="/dashboard")

DB_PATH = "database/diretrizes.db"

def get_conexao():
    return sqlite3.connect(DB_PATH)

@bp.route("/")
@login_required
@apenas_supervisor

def exibir_dashboard():
    conn = get_conexao()
    cursor = conn.cursor()

    # 1. Auditorias por agente
    cursor.execute("""
        SELECT agente_nome, COUNT(*) FROM auditorias
        GROUP BY agente_nome ORDER BY COUNT(*) DESC
    """)
    agentes_data = cursor.fetchall()
    agentes = [row[0] for row in agentes_data]
    qtd_por_agente = [row[1] for row in agentes_data]

    # 2. Pareceres por tipo
    cursor.execute("""
        SELECT TRIM(UPPER(SUBSTR(parecer, 1, 1)) || LOWER(SUBSTR(parecer, 2))) as parecer, COUNT(*)
        FROM auditorias
        GROUP BY parecer
    """)
    pareceres_data = cursor.fetchall()
    parecer_labels = [row[0] for row in pareceres_data]
    parecer_qtd = [row[1] for row in pareceres_data]

    # 3. Clientes que mais reclamam (parecer = Procedente)
    cursor.execute("""
        SELECT codigo_cliente, COUNT(*) FROM auditorias
        WHERE LOWER(parecer) = 'procedente'
        GROUP BY codigo_cliente
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    clientes_data = cursor.fetchall()
    clientes = [row[0] or "Desconhecido" for row in clientes_data]
    reclamacoes_por_cliente = [row[1] for row in clientes_data]

    # 4. Avaliações por supervisor agrupadas por parecer
    cursor.execute("""
        SELECT supervisor, parecer, COUNT(*) FROM auditorias
        GROUP BY supervisor, parecer
    """)
    supervisores_raw = cursor.fetchall()

    # Organiza dados por supervisor e parecer
    supervisores = {}
    for sup, parecer, total in supervisores_raw:
        if sup not in supervisores:
            supervisores[sup] = {"Procedente": 0, "Improcedente": 0, "Comentário Positivo Confirmado": 0}
        chave_normalizada = parecer.strip().lower()
        #Ajuste para considerar "positivo" e "elogio" como "Comentário Positivo Confirmado"
        if chave_normalizada == "procedente":
            supervisores[sup]["Procedente"] += total
        elif chave_normalizada == "improcedente":
            supervisores[sup]["Improcedente"] += total
        elif "positivo" in chave_normalizada or "comentário positivo" in chave_normalizada:
            supervisores[sup]["Comentário Positivo Confirmado"] += total


    supervisor_nomes = list(supervisores.keys())
    supervisor_procedente = [supervisores[s].get("Procedente", 0) for s in supervisor_nomes]
    supervisor_improcedente = [supervisores[s].get("Improcedente", 0) for s in supervisor_nomes]
    supervisor_positivo = [supervisores[s].get("Comentário Positivo Confirmado", 0) for s in supervisor_nomes]

    # 5. Auditorias por agente responsável final (Procedente, Improcedente, Elogiado)
    # Define os pareceres normalizados que queremos buscar
    parecer_procedente = "Procedente"
    parecer_improcedente = "Improcedente"
    parecer_elogiado = "Comentário positivo confirmado" # Ajuste se o nome exato for diferente nos seus dados normalizados

    # SQL para buscar as contagens de cada tipo de parecer por agente
    # Usamos a mesma normalização de 'parecer' que é usada para gerar 'parecer_labels'
    # Adicionamos "AND responsavel IS NOT NULL AND responsavel != ''" para evitar erros com responsáveis vazios/nulos
    cursor.execute(f"""
        SELECT
            responsavel,
            SUM(CASE WHEN TRIM(UPPER(SUBSTR(parecer, 1, 1)) || LOWER(SUBSTR(parecer, 2))) = ? THEN 1 ELSE 0 END) as qtd_procedente,
            SUM(CASE WHEN TRIM(UPPER(SUBSTR(parecer, 1, 1)) || LOWER(SUBSTR(parecer, 2))) = ? THEN 1 ELSE 0 END) as qtd_improcedente,
            SUM(CASE WHEN TRIM(UPPER(SUBSTR(parecer, 1, 1)) || LOWER(SUBSTR(parecer, 2))) = ? THEN 1 ELSE 0 END) as qtd_elogiado
        FROM auditorias
        WHERE responsavel IS NOT NULL AND TRIM(responsavel) != ''
        GROUP BY responsavel
        ORDER BY responsavel ASC
    """, (parecer_procedente, parecer_improcedente, parecer_elogiado))

    agentes_stats_data = cursor.fetchall()

    agentes_nomes_responsavel = [row[0] for row in agentes_stats_data]
    agentes_qtd_procedente = [row[1] for row in agentes_stats_data]
    agentes_qtd_improcedente = [row[2] for row in agentes_stats_data]
    agentes_qtd_elogiado = [row[3] for row in agentes_stats_data]




    # 6. Desempenho dos Critérios de Julgamento
    criterios_definicoes = [
        {"nome_exibicao": "Tempo de Resposta", "coluna_db": "nota_tempo_resposta"},
        {"nome_exibicao": "Linguagem e Comunicação", "coluna_db": "nota_linguagem"},
        {"nome_exibicao": "Postura e Solução", "coluna_db": "nota_postura_solucao"},
        {"nome_exibicao": "Empatia e Clareza", "coluna_db": "nota_empatia_clareza"},
        {"nome_exibicao": "Encerramento e Conduta Final", "coluna_db": "nota_encerramento"},
        {"nome_exibicao": "Procedimentos Técnicos e Segurança", "coluna_db": "nota_proced_tecnicos"},
        {"nome_exibicao": "Comportamentos Falhos", "coluna_db": "nota_comport_falhos"}
    ]

    criterios_data = []
    for criterio_def in criterios_definicoes:
        nome_exibicao = criterio_def["nome_exibicao"]
        coluna_db = criterio_def["coluna_db"]

        cursor.execute(f"""
            SELECT COALESCE(AVG({coluna_db}), 0)
            FROM auditorias
            WHERE {coluna_db} IS NOT NULL
        """)
        avg_nota = cursor.fetchone()[0]
        criterios_data.append({"nome": nome_exibicao, "media": avg_nota})

    # Ordena os critérios pela média da nota (do menor para o maior)
    criterios_data_ordenados = sorted(criterios_data, key=lambda x: x['media'])

    criterio_labels = [c['nome'] for c in criterios_data_ordenados]
    criterio_medias = [round(c['media'], 2) for c in criterios_data_ordenados]

# --- FIM DO TRECHO A SER INSERIDO ---


    conn.close() # Esta linha já existe no seu código, não a remova. Ela encerra a conexão com o banco.
    print("Labels disponíveis:", parecer_labels) # Esta linha também já existe.
    print("--- DADOS PARA GRÁFICO DE RESPONSÁVEIS ---")
    print(f"agentes_nomes_responsavel: {agentes_nomes_responsavel}")
    print(f"agentes_qtd_procedente: {agentes_qtd_procedente}")
    print(f"agentes_qtd_improcedente: {agentes_qtd_improcedente}")
    print(f"agentes_qtd_elogiado: {agentes_qtd_elogiado}")
    print(f"Tipo de agentes_nomes_responsavel: {type(agentes_nomes_responsavel)}")

# ... (Seu código existente da função exibir_dashboard, que é o 'return render_template')

# Este é o return final da função exibir_dashboard.
# Você precisa adicionar 'criterio_labels' e 'criterio_medias' aqui.
    return render_template("dashboard.html",
        agentes=json.dumps(agentes),
        qtd_agentes=json.dumps(qtd_por_agente),
        #pareceres=json.dumps(parecer_labels), # Suas linhas originais comentadas, mantidas por referência
        #qtd_parecer=json.dumps(parecer_qtd),
        pareceres=parecer_labels,
        qtd_parecer=parecer_qtd,
        clientes=json.dumps(clientes),
        qtd_clientes=json.dumps(reclamacoes_por_cliente),
        supervisor_nomes=json.dumps(supervisor_nomes),
        supervisor_procedente=json.dumps(supervisor_procedente),
        supervisor_improcedente=json.dumps(supervisor_improcedente),
        supervisor_positivo=json.dumps(supervisor_positivo),
        agentes_nomes_responsavel=json.dumps(agentes_nomes_responsavel),
        agentes_qtd_procedente=json.dumps(agentes_qtd_procedente),
        agentes_qtd_improcedente=json.dumps(agentes_qtd_improcedente),
        agentes_qtd_elogiado=json.dumps(agentes_qtd_elogiado),
        # --- NOVAS VARIÁVEIS PARA O TEMPLATE ---
        criterio_labels=json.dumps(criterio_labels),
        criterio_medias=json.dumps(criterio_medias)
        # --- FIM DAS NOVAS VARIÁVEIS ---
    )




   
