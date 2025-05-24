# dashboard.py

from flask import Blueprint, render_template
import json

# --- IMPORTS DO BANCO DE DADOS (SQLAlchemy) ---
from database import db
from models import Auditoria, Agente # Importe Auditoria e Agente (se Agente for usado em alguma consulta)
# --- FIM DOS IMPORTS DO BANCO DE DADOS ---

from routes.auth import login_required, apenas_supervisor


bp = Blueprint('dashboard', __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
@apenas_supervisor
def exibir_dashboard():
    # 1. Auditorias por agente
    agentes_data = db.session.query(
        Auditoria.agente_nome,
        db.func.count(Auditoria.id)
    ).group_by(Auditoria.agente_nome).order_by(db.func.count(Auditoria.id).desc()).all()
    agentes = [row[0] for row in agentes_data]
    qtd_por_agente = [row[1] for row in agentes_data]

    # 2. Pareceres por tipo
    pareceres_raw = db.session.query(
        Auditoria.parecer,
        db.func.count(Auditoria.id)
    ).group_by(Auditoria.parecer).all()

    # Mapeia pareceres brutos para pareceres normalizados e conta
    pareceres_contagem = {
        "Comentário positivo confirmado": 0,
        "Improcedente": 0,
        "Procedente": 0
    }

    for parecer, count in pareceres_raw:
        normalizado = parecer.strip() # Não use .lower() ainda, compare depois
        if "Comentário positivo confirmado" == normalizado:
            pareceres_contagem["Comentário positivo confirmado"] += count
        elif "Improcedente" == normalizado:
            pareceres_contagem["Improcedente"] += count
        elif "Procedente" == normalizado:
            pareceres_contagem["Procedente"] += count

    parecer_labels = list(pareceres_contagem.keys())
    parecer_qtd = list(pareceres_contagem.values())


    # 3. Clientes que mais reclamam (parecer = Procedente)
    clientes_data = db.session.query(
        Auditoria.codigo_cliente,
        db.func.count(Auditoria.id)
    ).filter(db.func.lower(Auditoria.parecer) == 'procedente').\
    group_by(Auditoria.codigo_cliente).\
    order_by(db.func.count(Auditoria.id).desc()).\
    limit(10).all()
    clientes = [row[0] or "Desconhecido" for row in clientes_data]
    reclamacoes_por_cliente = [row[1] for row in clientes_data]

    # 4. Avaliações por supervisor agrupadas por parecer
    supervisores_raw = db.session.query(
        Auditoria.supervisor,
        Auditoria.parecer,
        db.func.count(Auditoria.id)
    ).group_by(Auditoria.supervisor, Auditoria.parecer).all()

    # Organiza dados por supervisor e parecer
    supervisores = {}
    for sup, parecer, total in supervisores_raw:
        if sup not in supervisores:
            supervisores[sup] = {"Procedente": 0, "Improcedente": 0, "Comentário Positivo Confirmado": 0}
        chave_normalizada = parecer.strip() # Não use .lower() ainda
        if "Procedente" == chave_normalizada:
            supervisores[sup]["Procedente"] += total
        elif "Improcedente" == chave_normalizada:
            supervisores[sup]["Improcedente"] += total
        elif "Comentário positivo confirmado" == chave_normalizada:
            supervisores[sup]["Comentário Positivo Confirmado"] += total

    supervisor_nomes = list(supervisores.keys())
    supervisor_procedente = [supervisores[s].get("Procedente", 0) for s in supervisor_nomes]
    supervisor_improcedente = [supervisores[s].get("Improcedente", 0) for s in supervisor_nomes]
    supervisor_positivo = [supervisores[s].get("Comentário Positivo Confirmado", 0) for s in supervisor_nomes]

    # 5. Auditorias por Agente (Parecer) - Novo gráfico para o dashboard.html
    agentes_parecer_data = db.session.query(
        Auditoria.responsavel,
        Auditoria.parecer,
        db.func.count(Auditoria.id)
    ).filter(Auditoria.responsavel.isnot(None))\
    .group_by(Auditoria.responsavel, Auditoria.parecer)\
    .order_by(db.func.count(Auditoria.id).desc()).all()

    agentes_pareceres = {}
    for responsavel, parecer, total in agentes_parecer_data:
        if responsavel not in agentes_pareceres:
            agentes_pareceres[responsavel] = {"Procedente": 0, "Improcedente": 0, "Elogiado": 0}

        chave_normalizada = parecer.strip() # Não use .lower() ainda
        if "Procedente" == chave_normalizada:
            agentes_pareceres[responsavel]["Procedente"] += total
        elif "Improcedente" == chave_normalizada:
            agentes_pareceres[responsavel]["Improcedente"] += total
        elif "Comentário positivo confirmado" == chave_normalizada:
            agentes_pareceres[responsavel]["Elogiado"] += total # O nome da label no gráfico é "Elogiado"

    agentes_nomes_responsavel = list(agentes_pareceres.keys())
    agentes_qtd_procedente = [agentes_pareceres[a].get("Procedente", 0) for a in agentes_nomes_responsavel]
    agentes_qtd_improcedente = [agentes_pareceres[a].get("Improcedente", 0) for a in agentes_nomes_responsavel]
    agentes_qtd_elogiado = [agentes_pareceres[a].get("Elogiado", 0) for a in agentes_nomes_responsavel]


    # 6. Desempenho dos Critérios de Julgamento
    criterios_definicoes = [
        {"nome_exibicao": "Tempo de Resposta", "coluna_db": Auditoria.nota_tempo_resposta},
        {"nome_exibicao": "Linguagem e Comunicação", "coluna_db": Auditoria.nota_linguagem},
        {"nome_exibicao": "Postura e Solução", "coluna_db": Auditoria.nota_postura_solucao},
        {"nome_exibicao": "Empatia e Clareza", "coluna_db": Auditoria.nota_empatia_clareza},
        {"nome_exibicao": "Encerramento e Conduta Final", "coluna_db": Auditoria.nota_encerramento},
        {"nome_exibicao": "Procedimentos Técnicos e Segurança", "coluna_db": Auditoria.nota_proced_tecnicos},
        {"nome_exibicao": "Comportamentos Falhos", "coluna_db": Auditoria.nota_comport_falhos}
    ]

    criterios_data = []
    for criterio_def in criterios_definicoes:
        nome_exibicao = criterio_def["nome_exibicao"]
        coluna_db_model = criterio_def["coluna_db"]

        avg_nota = db.session.query(db.func.coalesce(db.func.avg(coluna_db_model), 0)).\
                   filter(coluna_db_model.isnot(None)).scalar()

        criterios_data.append({"nome": nome_exibicao, "media": avg_nota})

    criterios_data_ordenados = sorted(criterios_data, key=lambda x: x['media'])

    criterio_labels = [c['nome'] for c in criterios_data_ordenados]
    criterio_medias = [round(c['media'], 2) for c in criterios_data_ordenados]


    return render_template("dashboard.html",
        agentes=json.dumps(agentes),
        qtd_agentes=json.dumps(qtd_por_agente),
        pareceres=parecer_labels, # Lista de labels normalizadas
        qtd_parecer=parecer_qtd,   # Lista de quantidades correspondentes
        clientes=json.dumps(clientes),
        qtd_clientes=json.dumps(reclamacoes_por_cliente),
        supervisor_nomes=json.dumps(supervisor_nomes),
        supervisor_procedente=json.dumps(supervisor_procedente),
        supervisor_improcedente=json.dumps(supervisor_improcedente),
        supervisor_positivo=json.dumps(supervisor_positivo),
        agentes_nomes_responsavel=json.dumps(agentes_nomes_responsavel), # Novo para o gráfico de responsáveis
        agentes_qtd_procedente=json.dumps(agentes_qtd_procedente),
        agentes_qtd_improcedente=json.dumps(agentes_qtd_improcedente),
        agentes_qtd_elogiado=json.dumps(agentes_qtd_elogiado),
        criterio_labels=json.dumps(criterio_labels),
        criterio_medias=json.dumps(criterio_medias)
    )