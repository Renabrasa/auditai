import sqlite3,json

DB_PATH = "database/diretrizes.db"

def listar_todas_diretrizes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT texto FROM diretrizes ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def obter_diretrizes_atuais():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT texto FROM diretrizes ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

import sqlite3

def salvar_diretrizes(texto):
    if texto:
        texto = texto.strip()
    else:
        texto = ''

    conn = sqlite3.connect(DB_PATH) # ajuste o nome se for diferente
    cursor = conn.cursor()
    cursor.execute("INSERT INTO diretrizes (texto) VALUES (?)", (texto,))
    conn.commit()
    conn.close()



def buscar_agente_por_email(email):
    import sqlite3
    email = email.strip().lower()
    conn = sqlite3.connect("database/diretrizes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nome, supervisor, equipe FROM agentes WHERE lower(email) = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "nome": row[0],
            "supervisor": row[1],
            "equipe": row[2]
        }
    return None
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
                        nota_comport_falhos=None
                        
                        ):
    import json
    
    
    
    conn = sqlite3.connect("database/diretrizes.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO auditorias (
            agente_nome, agente_email, equipe, supervisor,
            numero_atendimento, codigo_cliente,
            parecer, justificativa,
            tempo_total, tempo_medio_resposta,
            responsavel, nota,
            resumo, avaliacoes_json,
            comentario_cliente,
            nota_tempo_resposta, nota_linguagem, nota_postura_solucao,
            nota_empatia_clareza, nota_encerramento, nota_proced_tecnicos,
            nota_comport_falhos
            
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        agente_nome, agente_email, equipe, supervisor,
        numero_atendimento, codigo_cliente,
        parecer, justificativa,
        tempo_total, tempo_medio_resposta,
        responsavel, nota,
        resumo, json.dumps(avaliacoes_json or []),
        comentario_cliente,
        # --- NOVOS VALORES NA ORDEM CORRETA ---
        nota_tempo_resposta, nota_linguagem, nota_postura_solucao,
        nota_empatia_clareza, nota_encerramento, nota_proced_tecnicos,
        nota_comport_falhos
        # --- FIM DOS NOVOS VALORES ---
    ))

    conn.commit()
    conn.close()
