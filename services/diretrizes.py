# diretrizes.py

# --- IMPORTS NECESSÁRIOS ---
import json
from datetime import datetime
import traceback # Adicionado para melhor depuração
# --- FIM DOS IMPORTS ---

# --- IMPORTS DO BANCO DE DADOS (SQLAlchemy) ---
from database import db
from models import Auditoria, Usuario, Agente, Diretriz # Importe todos os modelos que você usa aqui
# --- FIM DOS IMPORTS DO BANCO DE DADOS ---


# --- [FUNÇÃO: listar_todas_diretrizes] ---
def listar_todas_diretrizes():
    """Lista todas as diretrizes de atendimento do banco de dados, ordenadas pela mais recente."""
    diretrizes = Diretriz.query.order_by(Diretriz.id.desc()).all()
    return [d.texto for d in diretrizes]


# --- [FUNÇÃO: obter_diretrizes_atuais] ---
def obter_diretrizes_atuais():
    """Obtém o texto da diretriz de atendimento mais recente."""
    diretriz = Diretriz.query.order_by(Diretriz.id.desc()).first()
    return diretriz.texto if diretriz else ""


# --- [FUNÇÃO: salvar_diretrizes] ---
def salvar_diretrizes(texto):
    """Salva uma nova diretriz de atendimento no banco de dados."""
    if texto:
        texto = texto.strip()
    else:
        texto = ''

    try:
        nova_diretriz = Diretriz(texto=texto)
        db.session.add(nova_diretriz)
        db.session.commit()
        print("✅ Diretriz salva com sucesso!")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao salvar diretriz: {e}")
        traceback.print_exc() # Imprime o stack trace completo
        return False


# --- [FUNÇÃO: buscar_agente_por_email] ---
def buscar_agente_por_email(email):
    """Busca informações de um agente pelo email."""
    email = email.strip().lower()
    agente = Agente.query.filter(db.func.lower(Agente.email) == email).first()
    if agente:
        return {
            "nome": agente.nome,
            "supervisor": agente.supervisor,
            "equipe": agente.equipe
        }
    return None


# --- [FUNÇÃO: registrar_auditoria] ---
def registrar_auditoria(agente_nome, agente_email, equipe, supervisor,
                        numero_atendimento, codigo_cliente,
                        parecer, justificativa,
                        tempo_total, tempo_medio_resposta,
                        responsavel=None, nota=None,
                        resumo=None, avaliacoes_json=None,
                        comentario_cliente=None,
                        nota_tempo_resposta=None,
                        nota_linguagem=None,
                        nota_postura_solucao=None,
                        nota_empatia_clareza=None,
                        nota_encerramento=None,
                        nota_proced_tecnicos=None,
                        nota_comport_falhos=None):
    """Registra uma nova auditoria no banco de dados."""

    print("--- Tentando registrar auditoria ---")
    print(f"Agente: {agente_nome}, Atendimento: {numero_atendimento}, Parecer: {parecer}")

    try:
        nova_auditoria = Auditoria(
            agente_nome=agente_nome,
            agente_email=agente_email,
            equipe=equipe,
            supervisor=supervisor,
            numero_atendimento=numero_atendimento,
            codigo_cliente=codigo_cliente,
            parecer=parecer,
            justificativa=justificativa,
            tempo_total=tempo_total,
            tempo_medio_resposta=tempo_medio_resposta,
            responsavel=responsavel,
            nota=nota,
            resumo=resumo,
            avaliacoes_json=json.dumps(avaliacoes_json or []), # Continua serializando JSON
            comentario_cliente=comentario_cliente,
            nota_tempo_resposta=nota_tempo_resposta,
            nota_linguagem=nota_linguagem,
            nota_postura_solucao=nota_postura_solucao,
            nota_empatia_clareza=nota_empatia_clareza,
            nota_encerramento=nota_encerramento,
            nota_proced_tecnicos=nota_proced_tecnicos,
            nota_comport_falhos=nota_comport_falhos
        )
        db.session.add(nova_auditoria)
        db.session.commit()
        print("✅ Auditoria registrada com sucesso (via SQLAlchemy).")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO ao registrar auditoria (via SQLAlchemy): {e}")
        traceback.print_exc() # Imprime o stack trace completo do erro para depuração
        return False

# --- FIM DO ARQUIVO DIRETRIZES.PY ---