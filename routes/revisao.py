# revisao.py

# --- IMPORTS NECESSÁRIOS ---
from flask import Blueprint, render_template, redirect, url_for, request, flash # Adicionado 'flash'
# REMOVA ESTAS LINHAS:
# import sqlite3
# from flask import Flask, render_template # Flask e render_template já importados na primeira linha
# --- FIM DOS IMPORTS ---

# --- IMPORTS DO BANCO DE DADOS (SQLAlchemy) ---
from database import db
from models import Auditoria # Importa o modelo Auditoria
# --- FIM DOS IMPORTS DO BANCO DE DADOS ---

from routes.auth import login_required, apenas_supervisor


bp = Blueprint("revisao", __name__, url_prefix="/revisao")

# REMOVA ESTA LINHA, não é mais necessária com SQLAlchemy:
# def get_conexao():
#    return sqlite3.connect("database/diretrizes.db")


# --- [ROTA: PAINEL DE REVISÃO] ---
@bp.route("/")
@login_required
@apenas_supervisor
def painel_revisao():
    # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
    # conn = sqlite3.connect("database/diretrizes.db")
    # conn.row_factory = sqlite3.Row
    # cursor = conn.cursor()
    # cursor.execute("""
    #     SELECT * FROM auditorias
    #     WHERE LOWER(avaliacao_supervisor) = 'errado'
    #     ORDER BY data DESC
    # """)
    # auditorias = cursor.fetchall()
    # conn.close()
    # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
    auditorias = Auditoria.query.\
        filter(db.func.lower(Auditoria.avaliacao_supervisor) == 'errado').\
        order_by(Auditoria.data.desc()).all()
    # <--- FIM DA SUBSTITUIÇÃO ---

    return render_template("revisao_com_motivo.html", auditorias=auditorias)


# --- [ROTA: SALVAR MOTIVO DO ERRO] ---
@bp.route("/salvar", methods=["POST"])
@login_required # Supervisor precisa estar logado para salvar motivo
@apenas_supervisor # Apenas supervisor pode salvar motivo
def salvar_motivo_erro():
    auditoria_id = request.form.get("auditoria_id")
    motivo = request.form.get("motivo")

    if not auditoria_id or motivo is None: # motivo pode ser string vazia, mas não None
        flash("Dados incompletos para salvar o motivo do erro.", "warning")
        return redirect(url_for("revisao.painel_revisao"))

    try:
        # <--- SUBSTITUA O CÓDIGO SQLITE3 ABAIXO ---
        # conn = sqlite3.connect("database/diretrizes.db")
        # cursor = conn.cursor()
        # cursor.execute("""
        #     UPDATE auditorias
        #     SET motivo_erro = ?
        #     WHERE id = ?
        # """, (motivo.strip(), auditoria_id))
        # conn.commit()
        # conn.close()
        # <--- PELO CÓDIGO SQLAlchemy ABAIXO ---
        auditoria_para_atualizar = Auditoria.query.get(auditoria_id)
        if auditoria_para_atualizar:
            auditoria_para_atualizar.motivo_erro = motivo.strip()
            db.session.commit()
            flash("Motivo do erro salvo com sucesso!", "success")
        else:
            flash(f"Auditoria com ID {auditoria_id} não encontrada para atualizar motivo.", "danger")
        # <--- FIM DA SUBSTITUIÇÃO ---
    except Exception as e:
        db.session.rollback() # Desfaz a transação em caso de erro
        print(f"❌ Erro ao salvar motivo do erro: {str(e)}")
        flash(f"Erro ao salvar motivo do erro: {str(e)}", "danger")

    return redirect(url_for("revisao.painel_revisao"))