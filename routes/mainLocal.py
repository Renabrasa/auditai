from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from services.auditor import analisar_atendimento, gerar_feedback # Adicionado gerar_feedback se não estiver
from services.extrator import extrair_dados_transcricao, segmentar_transcricao # segmentar_transcricao é crucial
from config import DEBUG_ANALISE # Assumindo que você tem este arquivo de configuração
import sqlite3
import html # Para escapar/desescapar HTML se necessário

# Se o seu Blueprint se chama 'main', mantenha. Se for 'bp', ajuste.
# Vou usar 'bp' como no seu arquivo original.
bp = Blueprint("main", __name__, url_prefix="/")

@bp.route("/", methods=["GET", "POST"])
def index():
    resultado = None
    info_geral_atendimento = {} # Para dados gerais extraídos da transcrição completa
    transcricao_completa_form = ""
    reclamacao_geral_form = ""
    feedback_html = None # Renomeado de 'feedback' para evitar conflito com a função

    # Para repopular o formulário em caso de recarregamento da página após POST
    # Se estes valores vierem do Flask para o template, o JavaScript já os usa.
    # No Python, vamos lê-los do request.form.
    email_agente_selecionado_form = request.form.get("email_agente_especifico", "") if request.method == "POST" else ""
    estrelas_agente_form_str = request.form.get("estrelas_agente_especifico", "") if request.method == "POST" else ""


    if request.method == "POST":
        transcricao_completa_form = request.form.get("transcricao", "").strip()
        reclamacao_geral_form = request.form.get("reclamacao", "").strip()
        tipo_avaliacao = request.form.get("tipo_avaliacao", "reclamacao").strip().lower()
        numero_manual = request.form.get("numero_atendimento_manual", "").strip()
        codigo_manual = request.form.get("codigo_cliente_manual", "").strip()

        # Lê os novos campos do formulário
        email_agente_selecionado_form = request.form.get("email_agente_especifico", "").strip().lower()
        estrelas_agente_form_str = request.form.get("estrelas_agente_especifico", "").strip()

        estrelas_para_analise = None
        if estrelas_agente_form_str.isdigit():
            temp_estrelas = int(estrelas_agente_form_str)
            if 1 <= temp_estrelas <= 5:
                estrelas_para_analise = temp_estrelas

        # Lógica de comentário padrão (do seu código original)
        if not reclamacao_geral_form:
            if tipo_avaliacao == "elogio":
                reclamacao_geral_form = "O cliente elogiou o atendimento, mas não deixou comentário adicional."
            elif tipo_avaliacao == "neutro":
                reclamacao_geral_form = "O cliente não deixou comentário ou não se manifestou."
            else: # padrão para 'reclamacao' ou qualquer outro valor
                reclamacao_geral_form = "O cliente não deixou comentário."

        # Extrai informações gerais da transcrição completa sempre
        # A função extrair_dados_transcricao já retorna 'participantes'
        if transcricao_completa_form:
            info_geral_atendimento = extrair_dados_transcricao(transcricao_completa_form) or {}
        else:
            info_geral_atendimento = {}


        # Permite sobrescrever manualmente número do atendimento e código do cliente
        if numero_manual:
            info_geral_atendimento["numero_atendimento"] = numero_manual
        if codigo_manual:
            info_geral_atendimento["codigo_cliente"] = codigo_manual
        
        # Variáveis para a chamada de analisar_atendimento
        segmento_linhas_para_ia = None
        
        if not transcricao_completa_form and email_agente_selecionado_form:
            resultado = {"status": "erro", "parecer": "Erro", "justificativa": "A transcrição é necessária para analisar um agente específico."}
        elif not transcricao_completa_form and not email_agente_selecionado_form:
             resultado = {"status": "erro", "parecer": "Erro", "justificativa": "A transcrição do atendimento é obrigatória."}
        else:
            if email_agente_selecionado_form: # Se um agente específico foi selecionado para auditoria
                todos_segmentos = segmentar_transcricao(transcricao_completa_form)
                segmento_encontrado = False
                for segmento in todos_segmentos:
                    if segmento.get("agente_email") == email_agente_selecionado_form:
                        segmento_linhas_para_ia = segmento.get("linhas_segmento")
                        segmento_encontrado = True
                        break
                
                if not segmento_encontrado:
                    print(f"AVISO: Agente específico {email_agente_selecionado_form} não encontrado nos segmentos.")
                    resultado = {"status": "erro", "parecer": "Erro", "justificativa": f"Agente {email_agente_selecionado_form} não encontrado na transcrição fornecida."}
                else:
                    # Chama analisar_atendimento para o segmento específico
                    if DEBUG_ANALISE:
                        resultado = analisar_atendimento(
                            transcricao_completa=transcricao_completa_form, 
                            comentario_cliente_geral=reclamacao_geral_form,
                            segmento_auditado_linhas=segmento_linhas_para_ia,
                            email_agente_auditado=email_agente_selecionado_form,
                            estrelas_agente_auditado=estrelas_para_analise
                        )
                    else: # Modo simulação
                        resultado = {"status": "sucesso", "parecer": "Improcedente (Simulado)", "justificativa": "Simulação ativa. Nenhuma análise real foi feita para o agente específico.", "detalhes": {"pontuacao_final": 0}}


            else: # Nenhum agente específico selecionado, auditar a transcrição completa
                if DEBUG_ANALISE:
                    resultado = analisar_atendimento(
                        transcricao_completa=transcricao_completa_form, 
                        comentario_cliente_geral=reclamacao_geral_form
                        # Os outros params (segmento, email_agente, estrelas) serão None por padrão na função
                    )
                else: # Modo simulação
                     resultado = {"status": "sucesso", "parecer": "Improcedente (Simulado)", "justificativa": "Simulação ativa. Nenhuma análise real foi feita para a transcrição geral.", "detalhes": {"pontuacao_final": 0}}

        # Processamento do resultado da IA (seu código original, adaptado)
        if resultado and resultado.get("status") == "sucesso":
            # Sua lógica de normalizar parecer, ajustar justificativa, etc.
            # Exemplo de como você tratava antes (ajuste conforme sua lógica atual em auditor.py)
            just = resultado.get("justificativa", "")
            parecer_da_ia = resultado.get("parecer", "").lower() # Parecer vindo da IA (ou do seu cálculo)

            # Sua lógica de normalização de parecer (exemplo, pode ser mais complexa)
            if "improcedente" in parecer_da_ia:
                resultado["parecer"] = "Improcedente"
            elif "procedente" in parecer_da_ia:
                resultado["parecer"] = "Procedente"
            elif "positivo" in parecer_da_ia or "elogio" in parecer_da_ia or "confirmado" in parecer_da_ia:
                resultado["parecer"] = "Comentário positivo confirmado"
            else:
                # Se o parecer da IA não for claro, ou se você sempre recalcular, ajuste aqui.
                # Por ora, vamos manter o que a IA retornou se não bater com os acima.
                resultado["parecer"] = resultado.get("parecer", "Indefinido")


            # Pega último ID da auditoria (seu código)
            # É importante que a auditoria seja registrada ANTES de tentar pegar o ID dela,
            # o que acontece dentro de analisar_atendimento.
            # O ID retornado por `analisar_atendimento` (se você modificar para retornar)
            # ou pego após o registro seria mais confiável.
            # Por enquanto, vamos assumir que `registrar_auditoria` é chamado dentro de `analisar_atendimento`
            # e o ID é para o modal/feedback.
            
            # Se o `registrar_auditoria` acontece dentro do `analisar_atendimento` e você quer o ID:
            # Uma forma seria modificar `analisar_atendimento` para retornar o ID da auditoria registrada.
            # Ou buscar aqui, mas pode pegar o ID errado se houver concorrência.
            # Vamos assumir que o `resultado` pode conter um `id_auditoria` se `analisar_atendimento` for modificado.
            # Se não, esta lógica de ID pode precisar de revisão.
            if not resultado.get("id_auditoria"): # Se o ID não veio do analisar_atendimento
                conn = sqlite3.connect("database/diretrizes.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM auditorias ORDER BY data DESC LIMIT 1")
                row = cursor.fetchone()
                conn.close()
                if row:
                    resultado["id"] = row[0] # Para o formulário de avaliação do supervisor
            else:
                resultado["id"] = resultado.get("id_auditoria")


            resultado["parecer"] = resultado.get("parecer", "Indefinido").strip().capitalize()
            feedback_html = gerar_feedback(resultado.get("parecer"), resultado.get("justificativa"), resultado.get("detalhes"))
        
        elif resultado and resultado.get("status") == "erro":
            feedback_html = f"<p><strong>Erro na Análise:</strong> {html.escape(resultado.get('justificativa', 'Ocorreu um problema.'))}</p>"
            # Garante que 'resultado' não seja None para o template não quebrar
            if resultado is None: resultado = {}


    return render_template(
        "index.html",
        resultado=resultado,
        info=info_geral_atendimento, # info_geral_atendimento já contém 'participantes'
        transcricao=transcricao_completa_form,
        reclamacao=reclamacao_geral_form,
        feedback=feedback_html, # Nome da variável para o template
        # Para repopular o formulário
        email_agente_especifico=email_agente_selecionado_form, 
        estrelas_agente_especifico=estrelas_agente_form_str
    )

# Suas outras rotas (/extrair, /avaliar, /relatorio, /auditorias, /usuarios, etc.) continuam aqui...
# Certifique-se que a rota /extrair está usando a versão atualizada de extrair_dados_transcricao.
# Exemplo da sua rota /extrair (deve estar em main.py ou em extrair.py e importada corretamente)
@bp.route("/extrair", methods=["POST"])
def extrair():
    data = request.get_json()
    transcricao = data.get("transcricao", "")
    # A função extrair_dados_transcricao já foi atualizada para incluir 'participantes'
    info = extrair_dados_transcricao(transcricao) 
    return jsonify(info)



@bp.route("/avaliar", methods=["POST"])
def avaliar_parecer():
    auditoria_id = request.form.get("auditoria_id")
    avaliacao = request.form.get("avaliacao")

    print("📩 Avaliação recebida:")
    print("→ ID da auditoria:", auditoria_id)
    print("→ Avaliação:", avaliacao)

    if not auditoria_id or not avaliacao:
        print("❌ Dados incompletos. Redirecionando.")
        return redirect(url_for("main.index"))

    try:
        conn = sqlite3.connect("database/diretrizes.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE auditorias
            SET avaliacao_supervisor = ?
            WHERE id = ?
        """, (avaliacao.lower(), auditoria_id))
        conn.commit()
        conn.close()
        print("✅ Avaliação gravada com sucesso no banco de dados.")
    except Exception as e:
        print("❌ Erro ao gravar no banco:", str(e))

    return redirect(url_for("main.index"))


import json
import re
from datetime import datetime
from routes.auth import login_required, apenas_supervisor
@bp.route("/relatorio")
@bp.route("/relatorio/<int:id>")
@login_required
def relatorio(id):
    import json, re
    from datetime import datetime

    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM auditorias WHERE id = ?", (id,))
    auditoria = cursor.fetchone()

    if not auditoria:
        return "<h2>Atendimento não encontrado.</h2>", 404

    avaliacoes = []
    nota_final = auditoria["nota"]  # já está no banco

    try:
        raw = auditoria["resposta_completa"]
        if raw:
            json_obj = json.loads(raw)
            conteudo = json_obj["choices"][0]["message"]["content"]
            json_texto = re.search(r"\{.*\}", conteudo, re.DOTALL).group(0)
            dados = json.loads(json_texto)
            avaliacoes = dados.get("avaliacoes", [])
    except Exception as e:
        print("Erro ao extrair avaliações:", e)

    try:
        data_auditoria = datetime.strptime(auditoria["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except:
        data_auditoria = auditoria.get("data", "Data indisponível")

    return render_template(
        "relatorio.html",
        auditoria=auditoria,
        avaliacoes=avaliacoes,
        data_auditoria=data_auditoria,
        nota_final=nota_final
    )

@bp.route("/auditorias")
@login_required
def auditorias():
    import sqlite3, json
    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Coleta os filtros da URL
    criterio_filtro = request.args.get("criterio")
    nota_maxima = request.args.get("nota_maxima")
    email_agente = request.args.get("email_agente")
    numero_atendimento = request.args.get("numero_atendimento")

    # Base da query
    if session["usuario_tipo"] == "agente":
        cursor.execute("SELECT * FROM auditorias WHERE agente_email = ? ORDER BY data DESC", (session["usuario_email"],))
    else:
        cursor.execute("SELECT * FROM auditorias ORDER BY data DESC")
    rows = cursor.fetchall()

    lista_auditorias = []
    criterios_unicos = set()

    for row in rows:
        try:
            avaliacoes = json.loads(row["avaliacoes_json"] or "[]")
        except:
            avaliacoes = []

        # Filtro por agente (email)
        if email_agente:
            if email_agente.strip().lower() not in (row["agente_email"] or "").lower():
                continue

        # Filtro por número de atendimento
        if numero_atendimento:
            if numero_atendimento.strip() not in (row["numero_atendimento"] or ""):
                continue

        # Filtro por critério e nota
        if criterio_filtro and nota_maxima:
            if not any(a["criterio"] == criterio_filtro and float(a["nota"]) <= float(nota_maxima) for a in avaliacoes if "criterio" in a and "nota" in a):
                continue

        for a in avaliacoes:
            if "criterio" in a:
                criterios_unicos.add(a["criterio"])

        lista_auditorias.append({
            "id": row["id"],
            "numero_atendimento": row["numero_atendimento"],
            "codigo_cliente": row["codigo_cliente"],
            "data": row["data"],
            "parecer": row["parecer"],
            "nota": row["nota"] or "-",
            "resumo": row["resumo"] or "-",
            "avaliacoes_json": avaliacoes,
            "agente_nome": row["agente_nome"] or "-",
            "comentario_cliente": row["comentario_cliente"] or "-"
        })

    conn.close()
    criterios_ordenados = sorted(criterios_unicos)
    return render_template("auditorias.html", auditorias=lista_auditorias, criterios=criterios_ordenados)





from flask import request, render_template, redirect, url_for
import sqlite3

# --- [ROTA PRINCIPAL: LISTAR e CADASTRAR USUÁRIOS] ---
@bp.route("/usuarios", methods=["GET", "POST"])
@login_required


def usuarios():
    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"].strip()
        tipo = request.form["tipo"]

        cursor.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                       (nome, email, senha, tipo))
        conn.commit()

    cursor.execute("SELECT * FROM usuarios ORDER BY criado_em DESC")
    usuarios = cursor.fetchall()
    conn.close()

    return render_template("usuarios.html", usuarios=usuarios)


# --- [EDITAR USUÁRIO] ---
@bp.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@login_required
@apenas_supervisor

def editar_usuario(id):
    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        tipo = request.form["tipo"]

        cursor.execute("UPDATE usuarios SET nome = ?, email = ?, tipo = ? WHERE id = ?",
                       (nome, email, tipo, id))
        conn.commit()
        conn.close()
        return redirect(url_for("main.usuarios"))

    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (id,))
    usuario = cursor.fetchone()
    conn.close()

    return f"""
    <h2>Editar Usuário</h2>
    <form method="POST">
        <input type="text" name="nome" value="{usuario['nome']}" required>
        <input type="email" name="email" value="{usuario['email']}" required>
        <select name="tipo">
            <option value="agente" {'selected' if usuario['tipo']=='agente' else ''}>Agente</option>
            <option value="supervisor" {'selected' if usuario['tipo']=='supervisor' else ''}>Supervisor</option>
            <option value="admin" {'selected' if usuario['tipo']=='admin' else ''}>Administrador</option>
        </select>
        <button type="submit">Salvar</button>
    </form>
    """


# --- [ALTERAR SENHA] ---
@bp.route("/usuarios/senha/<int:id>", methods=["GET", "POST"])
@login_required

def alterar_senha(id):
    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if session["usuario_tipo"] == "agente" and session["usuario_id"] != id:
        return redirect("/")  # ou erro

    if request.method == "POST":
        nova_senha = request.form["senha"].strip()
        cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova_senha, id))
        conn.commit()
        conn.close()
        return redirect(url_for("main.usuarios"))

    cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (id,))
    usuario = cursor.fetchone()
    conn.close()

    return f"""
    <h2>Alterar Senha de {usuario['nome']}</h2>
    <form method="POST">
        <input type="password" name="senha" placeholder="Nova senha" required>
        <button type="submit">Atualizar Senha</button>
    </form>
    """


# --- [EXCLUIR USUÁRIO] ---
@bp.route("/usuarios/excluir/<int:id>")
@login_required
@apenas_supervisor

def excluir_usuario(id):
    conn = sqlite3.connect("database/diretrizes.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("main.usuarios"))


@bp.route("/agentes_disponiveis")
def agentes_disponiveis():
    import sqlite3
    conn = sqlite3.connect("database/diretrizes.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT nome, email, supervisor, equipe FROM agentes ORDER BY nome ASC")
    agentes = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(agentes)

from flask import session, redirect, request, render_template, url_for, flash
import sqlite3

# --- LOGIN ---
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"].strip()

        conn = sqlite3.connect("database/diretrizes.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session["usuario_id"] = usuario["id"]
            session["usuario_email"] = usuario["email"]
            session["usuario_tipo"] = usuario["tipo"]
            session["usuario_nome"] = usuario["nome"]
            return redirect("/")
        else:
            return render_template("login.html", erro="E-mail ou senha inválidos.")

    return render_template("login.html")


# --- LOGOUT ---
@bp.route("/logout")
@login_required

def logout():
    session.clear()
    return redirect("/login")
