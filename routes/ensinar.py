from flask import Blueprint, render_template, request, redirect
from services.diretrizes import salvar_diretrizes, listar_todas_diretrizes, obter_diretrizes_atuais
from routes.auth import login_required, apenas_supervisor

bp = Blueprint('ensinar', __name__, url_prefix="/ensinar")


@bp.route("/", methods=["GET", "POST"])
@login_required
@apenas_supervisor
def ensinar():
    if request.method == 'POST':
        novo_texto = request.form.get('diretrizes', '').strip()
        if novo_texto:
            salvar_diretrizes(novo_texto)

    texto_salvo = obter_diretrizes_atuais() or ''
    return render_template('ensinar.html', diretrizes_texto=texto_salvo)
