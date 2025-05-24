# models.py

from database import db # Importa o objeto 'db' que definimos em database.py
from datetime import datetime # Para trabalhar com tipos de data e hora

class Auditoria(db.Model):
    __tablename__ = 'auditorias' # Nome da tabela no MySQL

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    agente_nome = db.Column(db.String(255))
    agente_email = db.Column(db.String(255))
    equipe = db.Column(db.String(255))
    supervisor = db.Column(db.String(255))
    numero_atendimento = db.Column(db.String(255))
    codigo_cliente = db.Column(db.String(255))
    parecer = db.Column(db.String(255))
    justificativa = db.Column(db.Text)
    tempo_total = db.Column(db.Integer)
    tempo_medio_resposta = db.Column(db.Float)
    data = db.Column(db.DateTime, default=datetime.utcnow) # Ajuste para usar datetime.utcnow ou datetime.now
    avaliacao_supervisor = db.Column(db.String(255), default=None)
    motivo_erro = db.Column(db.Text)
    responsavel = db.Column(db.String(255))
    nota = db.Column(db.Float)
    resumo = db.Column(db.Text)
    avaliacoes_json = db.Column(db.Text) # JSON será salvo como texto
    comentario_cliente = db.Column(db.Text)
    nota_tempo_resposta = db.Column(db.Float)
    nota_linguagem = db.Column(db.Float)
    nota_postura_solucao = db.Column(db.Float)
    nota_empatia_clareza = db.Column(db.Float)
    nota_encerramento = db.Column(db.Float)
    nota_proced_tecnicos = db.Column(db.Float)
    nota_comport_falhos = db.Column(db.Float)

    def __repr__(self):
        return f"<Auditoria {self.id}>"

class Usuario(db.Model):
    __tablename__ = 'usuarios' # Nome da tabela no MySQL
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False, default='agente')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Usuario {self.email}>"

class Agente(db.Model):
    __tablename__ = 'agentes' # Nome da tabela no MySQL
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    supervisor = db.Column(db.String(255))
    equipe = db.Column(db.String(255))

    def __repr__(self):
        return f"<Agente {self.nome}>"

class Diretriz(db.Model):
    __tablename__ = 'diretrizes' # Nome da tabela no MySQL
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    texto = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow) # Assumindo que você tem uma coluna 'data' ou 'criado_em'

    def __repr__(self):
        return f"<Diretriz {self.id}>"