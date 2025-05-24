# database.py

from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def configure_db(app):
    # A URL de conexão é lida da variável de ambiente DATABASE_URL.
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    # Desativa o rastreamento de modificações do SQLAlchemy, o que é bom para performance.
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializa a extensão SQLAlchemy com a aplicação Flask.
    db.init_app(app)

    # Nota: Não usaremos db.create_all() aqui para não tentar recriar tabelas que já existem no MySQL.
    # A criação das tabelas já foi feita manualmente no DBeaver.