# agentes.py

# --- IMPORTS NECESSÁRIOS ---
from flask import Blueprint, render_template, request, redirect, url_for, flash # Adicionado 'flash'
# REMOVA ESTA LINHA: import sqlite3
# --- FIM DOS IMPORTS ---

# --- IMPORTS DO BANCO DE DADOS (SQLAlchemy) ---
from database import db
from models import Agente # Importa o modelo Agente
# --- FIM DOS IMPORTS DO BANCO DE DADOS ---

from routes.auth import login_required, apenas_supervisor


bp = Blueprint('agentes', __name__, url_prefix="/agentes")

# REMOVA ESTAS LINHAS, não são mais necessárias com SQLAlchemy:
# DB_PATH = "database/diretrizes.db"
# def get_conexao():
#    return sqlite3.connect(DB_PATH)


# --- [ROTA: LISTAR AGENTES] ---
@bp.route("/", methods=["GET"])
@login_required
@apenas_supervisor
def listar_agentes():
    # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
    # conn = get_conexao()
    # agentes = conn.execute("SELECT id, nome, email, supervisor, equipe FROM agentes ORDER BY nome").fetchall()
    # conn.close()
    # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
    agentes = Agente.query.order_by(Agente.nome.asc()).all()
    # <--- FIM DA SUBSTITUIÇÃO ---
    return render_template("agentes.html", agentes=agentes)


# --- [ROTA: CADASTRAR NOVO AGENTE] ---
@bp.route("/novo", methods=["POST"])
@login_required
@apenas_supervisor
def novo_agente():
    nome = request.form["nome"].strip()
    email = request.form["email"].strip().lower()
    supervisor = request.form["supervisor"].strip()
    equipe = request.form["equipe"].strip()

    try:
        # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
        # conn = get_conexao()
        # conn.execute("INSERT INTO agentes (nome, email, supervisor, equipe) VALUES (?, ?, ?, ?)",
        #              (nome, email, supervisor, equipe))
        # conn.commit()
        # conn.close()
        # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
        # Verifica se o email já existe antes de cadastrar
        if Agente.query.filter_by(email=email).first():
            flash(f"Agente com e-mail {email} já cadastrado.", "warning")
        else:
            novo_agente_obj = Agente(nome=nome, email=email, supervisor=supervisor, equipe=equipe)
            db.session.add(novo_agente_obj)
            db.session.commit()
            flash("Agente cadastrado com sucesso!", "success")
        # <--- FIM DA SUBSTITUIÇÃO ---
    except Exception as e:
        db.session.rollback() # Desfaz a transação em caso de erro
        print(f"Erro ao cadastrar agente: {e}")
        flash(f"Erro ao cadastrar agente: {e}", "danger")

    return redirect(url_for("agentes.listar_agentes"))


# --- [ROTA: EDITAR AGENTE] ---
@bp.route("/editar/<int:id>", methods=["GET", "POST"]) # Adicionado GET para exibir o formulário de edição
@login_required
@apenas_supervisor
def editar_agente(id):
    # <--- CÓDIGO PARA PEGAR O AGENTE PARA EDIÇÃO (MÉTODO GET) ---
    agente_para_editar = Agente.query.get(id)
    if not agente_para_editar:
        flash("Agente não encontrado.", "danger")
        return redirect(url_for("agentes.listar_agentes"))

    if request.method == "POST":
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        supervisor = request.form["supervisor"].strip()
        equipe = request.form["equipe"].strip()

        try:
            # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
            # conn = get_conexao()
            # conn.execute("UPDATE agentes SET nome=?, email=?, supervisor=?, equipe=? WHERE id=?",
            #              (nome, email, supervisor, equipe, id))
            # conn.commit()
            # conn.close()
            # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
            # Verifica se o novo email já existe e não é o do próprio agente
            if Agente.query.filter(Agente.email == email, Agente.id != id).first():
                flash(f"E-mail {email} já cadastrado para outro agente.", "warning")
            else:
                agente_para_editar.nome = nome
                agente_para_editar.email = email
                agente_para_editar.supervisor = supervisor
                agente_para_editar.equipe = equipe
                db.session.commit()
                flash("Agente atualizado com sucesso!", "success")
            # <--- FIM DA SUBSTITUIÇÃO ---
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao editar agente: {e}")
            flash(f"Erro ao editar agente: {e}", "danger")

        return redirect(url_for("agentes.listar_agentes"))
    
    # Renderiza o formulário de edição para o método GET
    # Você precisará ter um template 'editar_agente.html' para isso.
    return render_template("editar_agente.html", agente=agente_para_editar)


# --- [ROTA: EXCLUIR AGENTE] ---
@bp.route("/excluir/<int:id>", methods=["POST"]) # O método GET para exclusão direta não é recomendado
@login_required
@apenas_supervisor
def excluir_agente(id):
    try:
        # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
        # conn = get_conexao()
        # conn.execute("DELETE FROM agentes WHERE id=?", (id,))
        # conn.commit()
        # conn.close()
        # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
        agente_para_excluir = Agente.query.get(id)
        if agente_para_excluir:
            db.session.delete(agente_para_excluir)
            db.session.commit()
            flash("Agente excluído com sucesso!", "success")
        else:
            flash("Agente não encontrado para exclusão.", "danger")
        # <--- FIM DA SUBSTITUIÇÃO ---
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao excluir agente: {e}")
        flash(f"Erro ao excluir agente: {e}", "danger")

    return redirect(url_for("agentes.listar_agentes"))