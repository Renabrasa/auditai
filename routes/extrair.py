from flask import Blueprint, request, jsonify
from services.extrator import extrair_dados_transcricao

bp_extrair = Blueprint("extrair", __name__)

@bp_extrair.route("/extrair", methods=["POST"])
def extrair():
    data = request.get_json()
    transcricao = data.get("transcricao", "").strip()

    if not transcricao:
        return jsonify({}), 400

    info = extrair_dados_transcricao(transcricao)

    return jsonify({
        "numero_atendimento": info.get("numero_atendimento", ""),
        "codigo_cliente": info.get("codigo_cliente", ""),
        "nome_agente": info.get("nome_agente", ""),
        "email_agente": info.get("email_agente", ""),
        "equipe": info.get("equipe", ""),
        "hora_inicio": info.get("hora_inicio", ""),
        "tempo_total": info.get("tempo_total", ""),
        "tempo_medio_resposta": info.get("tempo_medio_resposta", "")
    })
