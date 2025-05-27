# main.py

# --- IMPORTS NECESSÁRIOS ---
from dotenv import load_dotenv
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from services.auditor import analisar_atendimento
from services.extrator import extrair_dados_transcricao, segmentar_transcricao
#from config import DEBUG_ANALISE
import os
DEBUG_ANALISE = os.environ.get("DEBUG_ANALISE", "False").lower() == "true"
from routes.auth import login_required, apenas_supervisor
import html # Para escapar/desescapar HTML se necessário
import json # Usado para manipular JSONs
from datetime import datetime # Usado para manipular datas
# --- FIM DOS IMPORTS ---

# --- IMPORTS DO BANCO DE DADOS (SQLAlchemy) ---
from database import db
from models import Auditoria, Usuario, Agente, Diretriz
# --- FIM DOS IMPORTS DO BANCO DE DADOS ---

bp = Blueprint("main", __name__, url_prefix="/")


# --- [ROTA PRINCIPAL: INDEX / HOME] ---
@bp.route("/", methods=["GET", "POST"])
@login_required # Garante que o usuário esteja logado
def index():
    resultado = None
    info_geral_atendimento = {} # Para dados gerais extraídos da transcrição completa
    transcricao_completa_form = ""
    reclamacao_geral_form = ""
    feedback_html = None # Renomeado de 'feedback' para evitar conflito com a função

    # Para repopular o formulário em caso de recarregamento da página após POST
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
            try:
                temp_estrelas = int(estrelas_agente_form_str)
                if 1 <= temp_estrelas <= 5: # Assumindo escala de 1 a 5 estrelas
                    estrelas_para_analise = temp_estrelas
            except ValueError:
                flash("Valor de estrelas inválido.", "warning")


        # Lógica de comentário padrão
        if not reclamacao_geral_form:
            if tipo_avaliacao == "elogio":
                reclamacao_geral_form = "O cliente elogiou o atendimento, mas não deixou comentário adicional."
            elif tipo_avaliacao == "neutro":
                reclamacao_geral_form = "O cliente não deixou comentário ou não se manifestou."
            else: # padrão para 'reclamacao' ou qualquer outro valor
                reclamacao_geral_form = "O cliente não deixou comentário."

        # Extrai informações gerais da transcrição completa sempre
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
            flash("A transcrição é necessária para analisar um agente específico.", "danger")
        elif not transcricao_completa_form and not email_agente_selecionado_form:
             resultado = {"status": "erro", "parecer": "Erro", "justificativa": "A transcrição do atendimento é obrigatória."}
             flash("A transcrição do atendimento é obrigatória.", "danger")
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
                    flash(f"Agente {email_agente_selecionado_form} não encontrado na transcrição fornecida.", "danger")
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
                        flash("Simulação ativa. Nenhuma análise real foi feita para o agente específico.", "info")


            else: # Nenhum agente específico selecionado, auditar a transcrição completa
                if DEBUG_ANALISE:
                    resultado = analisar_atendimento(
                        transcricao_completa=transcricao_completa_form,
                        comentario_cliente_geral=reclamacao_geral_form
                        # Os outros params (segmento, email_agente, estrelas) serão None por padrão na função
                    )
                else: # Modo simulação
                     resultado = {"status": "sucesso", "parecer": "Improcedente (Simulado)", "justificativa": "Simulação ativa. Nenhuma análise real foi feita para a transcrição geral.", "detalhes": {"pontuacao_final": 0}}
                     flash("Simulação ativa. Nenhuma análise real foi feita para a transcrição geral.", "info")

        # Processamento do resultado da IA
        if resultado and resultado.get("status") == "sucesso":
            just = resultado.get("justificativa", "")
            parecer_da_ia = resultado.get("parecer", "").lower()

            # Normalização do parecer
            if "improcedente" in parecer_da_ia:
                resultado["parecer"] = "Improcedente"
            elif "procedente" in parecer_da_ia:
                resultado["parecer"] = "Procedente"
            elif "positivo" in parecer_da_ia or "elogio" in parecer_da_ia or "confirmado" in parecer_da_ia:
                resultado["parecer"] = "Comentário positivo confirmado"
            else:
                resultado["parecer"] = resultado.get("parecer", "Indefinido")


            # Pega último ID da auditoria (agora do DB via SQLAlchemy)
            # É importante que a auditoria seja registrada ANTES de tentar pegar o ID dela,
            # o que acontece dentro de analisar_atendimento.
            # Se `analisar_atendimento` retorna o ID, use-o. Senão, busca aqui.
            if not resultado.get("id_auditoria"):
                ultima_auditoria = Auditoria.query.order_by(Auditoria.data.desc()).first()
                if ultima_auditoria:
                    resultado["id"] = ultima_auditoria.id
            else:
                resultado["id"] = resultado.get("id_auditoria")


            resultado["parecer"] = resultado["parecer"].strip().capitalize()
            feedback_html = gerar_feedback(resultado.get("parecer"), resultado.get("justificativa"), resultado.get("detalhes"))

        elif resultado and resultado.get("status") == "erro":
            feedback_html = f"<p><strong>Erro na Análise:</strong> {html.escape(resultado.get('justificativa', 'Ocorreu um problema.'))}</p>"
            if resultado is None: resultado = {} # Garantir que 'resultado' não seja None para o template

    return render_template(
        "index.html",
        resultado=resultado,
        info=info_geral_atendimento,
        transcricao=transcricao_completa_form,
        reclamacao=reclamacao_geral_form,
        feedback=feedback_html,
        email_agente_especifico=email_agente_selecionado_form,
        estrelas_agente_especifico=estrelas_agente_form_str
    )

# --- [ROTA: EXTRAIR DADOS (API)] ---
@bp.route("/extrair", methods=["POST"])
def extrair():
    data = request.get_json()
    transcricao = data.get("transcricao", "")
    info = extrair_dados_transcricao(transcricao)
    return jsonify(info)


# --- [ROTA: AVALIAR PARECER DO SUPERVISOR] ---
@bp.route("/avaliar", methods=["POST"])
@login_required # Supervisor precisa estar logado para avaliar
@apenas_supervisor # Apenas supervisor pode avaliar
def avaliar_parecer():
    auditoria_id = request.form.get("auditoria_id")
    avaliacao = request.form.get("avaliacao")

    print("📩 Avaliação recebida:")
    print("→ ID da auditoria:", auditoria_id)
    print("→ Avaliação:", avaliacao)

    if not auditoria_id or not avaliacao:
        print("❌ Dados incompletos. Redirecionando.")
        flash("Dados incompletos para avaliar a auditoria.", "warning")
        return redirect(url_for("main.index"))

    try:
        auditoria_para_atualizar = Auditoria.query.get(auditoria_id) # Busca a auditoria pelo ID
        if auditoria_para_atualizar:
            auditoria_para_atualizar.avaliacao_supervisor = avaliacao.lower()
            db.session.commit() # Salva a alteração no banco
            print("✅ Avaliação gravada com sucesso no banco de dados.")
            flash("Avaliação gravada com sucesso!", "success")
        else:
            print(f"❌ Auditoria com ID {auditoria_id} não encontrada para atualização.")
            flash(f"Auditoria com ID {auditoria_id} não encontrada.", "danger")

    except Exception as e:
        db.session.rollback() # Em caso de erro, desfaz a transação
        print(f"❌ Erro ao gravar no banco: {str(e)}")
        flash(f"Erro ao gravar a avaliação: {str(e)}", "danger")

    return redirect(url_for("main.index"))


# --- [ROTA: RELATÓRIO DE AUDITORIA] ---
@bp.route("/relatorio")
@bp.route("/relatorio/<int:id>")
@login_required
def relatorio(id):
    auditoria = Auditoria.query.get(id) # Busca a auditoria pelo ID

    if not auditoria:
        flash("Atendimento não encontrado.", "danger")
        return render_template("404.html", message="Atendimento não encontrado."), 404 # Melhor usar um template 404

    avaliacoes = []
    nota_final = auditoria.nota

    try:
        # Pega as avaliações diretamente do campo avaliacoes_json do objeto Auditoria
        if auditoria.avaliacoes_json:
            avaliacoes = json.loads(auditoria.avaliacoes_json)
    except Exception as e:
        print(f"Erro ao extrair avaliações do JSON para auditoria {id}: {e}")
        flash(f"Erro ao carregar detalhes das avaliações: {e}", "danger")

    try:
        # Formata a data que já é um objeto datetime
        data_auditoria = auditoria.data.strftime("%d/%m/%Y %H:%M")
    except:
        data_auditoria = "Data indisponível" # Fallback se data for inválida

    return render_template(
        "relatorio.html",
        auditoria=auditoria,
        avaliacoes=avaliacoes,
        data_auditoria=data_auditoria,
        nota_final=nota_final
    )


# --- [ROTA: LISTA DE AUDITORIAS] ---
@bp.route("/auditorias")
@login_required
def auditorias():
    # Inicia a query base
    query = Auditoria.query

    # Filtro por tipo de usuário (agente só vê as suas)
    if session.get("usuario_tipo") == "agente":
        query = query.filter_by(agente_email=session.get("usuario_email"))

    # Aplica ordenação
    query = query.order_by(Auditoria.data.desc())

    # Coleta os filtros da URL
    criterio_filtro = request.args.get("criterio")
    nota_maxima = request.args.get("nota_maxima")
    email_agente = request.args.get("email_agente")
    numero_atendimento = request.args.get("numero_atendimento")

    # Executa a query para pegar todos os objetos Auditoria antes dos filtros em Python
    lista_auditorias_obj = query.all()

    lista_auditorias = []
    criterios_unicos = set()

    for auditoria_obj in lista_auditorias_obj:
        try:
            # Acessa diretamente o atributo do objeto
            avaliacoes = json.loads(auditoria_obj.avaliacoes_json or "[]")
        except Exception as e:
            avaliacoes = []
            print(f"Erro ao parsear JSON para auditoria {auditoria_obj.id}: {auditoria_obj.avaliacoes_json} - Erro: {e}")
            flash(f"Erro ao carregar avaliações detalhadas para auditoria {auditoria_obj.id}", "warning")

        # Filtro por agente (email)
        if email_agente:
            if email_agente.strip().lower() not in (auditoria_obj.agente_email or "").lower():
                continue

        # Filtro por número de atendimento
        if numero_atendimento:
            if numero_atendimento.strip() not in (auditoria_obj.numero_atendimento or ""):
                continue

        # Filtro por critério e nota
        if criterio_filtro and nota_maxima:
            try:
                nota_maxima_float = float(nota_maxima)
                if not any(a.get("criterio") == criterio_filtro and float(a.get("nota", 0)) <= nota_maxima_float for a in avaliacoes):
                    continue
            except ValueError:
                flash("Nota máxima inválida para filtro.", "danger")
                continue # Pula para a próxima auditoria se a nota máxima for inválida

        # Coleta critérios únicos para o filtro dropdown
        for a in avaliacoes:
            if "criterio" in a:
                criterios_unicos.add(a["criterio"])

        lista_auditorias.append({
            "id": auditoria_obj.id,
            "numero_atendimento": auditoria_obj.numero_atendimento,
            "codigo_cliente": auditoria_obj.codigo_cliente,
            "data": auditoria_obj.data.strftime("%d/%m/%Y %H:%M") if auditoria_obj.data else "Data indisponível",
            "parecer": auditoria_obj.parecer,
            "nota": auditoria_obj.nota or "-",
            "resumo": auditoria_obj.resumo or "-",
            "avaliacoes_json": avaliacoes,
            "agente_nome": auditoria_obj.agente_nome or "-",
            "comentario_cliente": auditoria_obj.comentario_cliente or "-",
            "supervisor": auditoria_obj.supervisor or "-" # Incluir supervisor também, pode ser útil
        })

    criterios_ordenados = sorted(list(criterios_unicos))
    return render_template("auditorias.html", auditorias=lista_auditorias, criterios=criterios_ordenados)


# --- [ROTA: LISTAR e CADASTRAR USUÁRIOS] ---
@bp.route("/usuarios", methods=["GET", "POST"])
@login_required
@apenas_supervisor # Apenas supervisor pode acessar esta rota
def usuarios():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"].strip()
        tipo = request.form["tipo"]

        try:
            # Verifica se o email já existe para evitar duplicatas e erro UNIQUE
            if Usuario.query.filter_by(email=email).first():
                flash(f"E-mail {email} já cadastrado.", "warning")
            else:
                novo_usuario = Usuario(nome=nome, email=email, senha=senha, tipo=tipo)
                db.session.add(novo_usuario)
                db.session.commit()
                flash("Usuário cadastrado com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao cadastrar usuário: {e}")
            flash(f"Erro ao cadastrar usuário: {e}", "danger")

    usuarios = Usuario.query.order_by(Usuario.criado_em.desc()).all()

    return render_template("usuarios.html", usuarios=usuarios)


# --- [ROTA: EDITAR USUÁRIO] ---
@bp.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@login_required
@apenas_supervisor
def editar_usuario(id):
    usuario_para_editar = Usuario.query.get(id) # Busca o usuário pelo ID
    if not usuario_para_editar:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("main.usuarios")) # Redireciona se não encontrar

    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        tipo = request.form["tipo"]

        try:
            # Verifica se o novo email já existe e não é o do próprio usuário
            if Usuario.query.filter(Usuario.email == email, Usuario.id != id).first():
                flash(f"E-mail {email} já cadastrado para outro usuário.", "warning")
            else:
                usuario_para_editar.nome = nome
                usuario_para_editar.email = email
                usuario_para_editar.tipo = tipo
                db.session.commit()
                flash("Usuário atualizado com sucesso!", "success")
                return redirect(url_for("main.usuarios")) # Redireciona após sucesso
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao editar usuário: {e}")
            flash(f"Erro ao editar usuário: {e}", "danger")
            # Permite que o template renderize o erro se o redirect não ocorrer

    return render_template("editar_usuario.html", usuario=usuario_para_editar)


# --- [ROTA: ALTERAR SENHA] ---
@bp.route("/usuarios/senha/<int:id>", methods=["GET", "POST"])
@login_required
def alterar_senha(id):
    usuario_para_senha = Usuario.query.get(id)
    if not usuario_para_senha:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("main.usuarios"))

    # Verifica se o usuário logado tem permissão para alterar a senha
    # Admin/Supervisor podem alterar qualquer um. Agente só pode alterar a própria.
    if session.get("usuario_tipo") == "agente" and session.get("usuario_id") != int(id):
        flash("Você não tem permissão para alterar a senha de outro agente.", "danger")
        return redirect("/")

    if request.method == "POST":
        nova_senha = request.form["senha"].strip()
        if not nova_senha:
            flash("A senha não pode ser vazia.", "warning")
            return render_template("alterar_senha.html", usuario=usuario_para_senha)

        try:
            usuario_para_senha.senha = nova_senha # Atualiza a senha do objeto
            db.session.commit() # Salva no banco
            flash("Senha atualizada com sucesso!", "success")
            return redirect(url_for("main.usuarios"))
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao alterar senha: {e}")
            flash(f"Erro ao alterar senha: {e}", "danger")

    return render_template("alterar_senha.html", usuario=usuario_para_senha)


# --- [ROTA: EXCLUIR USUÁRIO] ---
@bp.route("/usuarios/excluir/<int:id>")
@login_required
@apenas_supervisor
def excluir_usuario(id):
    try:
        usuario_para_excluir = Usuario.query.get(id) # Busca o usuário
        if usuario_para_excluir:
            # Proteção: não permitir que um usuário exclua a si mesmo se for admin/supervisor
            if session.get("usuario_id") == int(id):
                flash("Você não pode excluir seu próprio usuário enquanto estiver logado.", "warning")
            else:
                db.session.delete(usuario_para_excluir) # Marca para exclusão
                db.session.commit() # Confirma a exclusão
                flash("Usuário excluído com sucesso!", "success")
        else:
            flash("Usuário não encontrado para exclusão.", "danger")
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir usuário: {e}")
        flash(f"Erro ao excluir usuário: {e}", "danger")

    return redirect(url_for("main.usuarios"))


# --- [ROTA: AGENTES DISPONÍVEIS (API)] ---
@bp.route("/agentes_disponiveis")
# Não precisa de login_required/apenas_supervisor se for uma API interna para todos logados
# Mas se quiser restringir, pode adicionar: @login_required
def agentes_disponiveis():
    agentes_obj = Agente.query.order_by(Agente.nome.asc()).all()
    # Converte a lista de objetos Agente em uma lista de dicionários
    agentes = [{
        "nome": agente.nome,
        "email": agente.email,
        "supervisor": agente.supervisor,
        "equipe": agente.equipe
    } for agente in agentes_obj]

    return jsonify(agentes)

# --- [FUNÇÃO: GERAR FEEDBACK PARA EXIBIÇÃO] ---
# Esta função foi movida para main.py para ser acessível às rotas que a usam.
def gerar_feedback(parecer: str, justificativa: str, detalhes: dict = None) -> str:
    """
    Formata o feedback da análise da IA em HTML para exibição na interface.

    Args:
        parecer: O parecer final (Procedente, Improcedente, Comentário positivo confirmado).
        justificativa: A justificativa final fornecida pela IA.
        detalhes: Dicionário contendo resumo, avaliações por critério e pontuação final.

    Returns:
        Uma string HTML formatada com o feedback.
    """
    if not detalhes:
        return "<p>Sem justificativa ou detalhes para exibir.</p>"

    resumo = html.escape(detalhes.get("resumo", "-"))
    avaliacoes = detalhes.get("avaliacoes", [])
    nota_final = detalhes.get("pontuacao_final", "-")

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
        # Define a cor com base na nota para melhor visualização
        cor_nota_css = "green" if nota_final >= 7 else ("orange" if nota_final >= 5 else "red")
        feedback_html_str += f"<p style='margin-top:1rem;'><strong>Pontuação Final Calculada:</strong> <span style='color:{cor_nota_css};font-weight:bold;font-size:1.2rem'>{nota_final}</span></p>"
    else:
        feedback_html_str += "<p><strong>Pontuação Final Calculada:</strong> -</p>"

    # Conclusão e justificativa final
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
    if justificativa:
        feedback_html_str += f"<p class='conclusao'><strong>Justificativa da IA:</strong> {html.escape(justificativa)}</p>"

    return feedback_html_str


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"].strip()

        # Usando o modelo Usuario e SQLAlchemy para buscar o usuário
        # Não é recomendado armazenar senhas em texto puro em produção!
        # Considere usar hashing de senhas (ex: Werkzeug.security.generate_password_hash)
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()

        if usuario:
            # Popula a sessão com os dados do usuário logado
            session["usuario_id"] = usuario.id
            session["usuario_email"] = usuario.email
            session["usuario_tipo"] = usuario.tipo
            session["usuario_nome"] = usuario.nome
            flash(f"Bem-vindo(a), {usuario.nome}!", "success") # Adiciona uma mensagem de sucesso
            return redirect("/")
        else:
            flash("E-mail ou senha inválidos.", "danger") # Adiciona uma mensagem de erro mais visível
            return render_template("login.html", erro="E-mail ou senha inválidos.") # Mantém o erro para o template, se preferir

    return render_template("login.html")

# --- LOGOUT ---
@bp.route("/logout")
@login_required

def logout():
    session.clear()
    return redirect("/login")
