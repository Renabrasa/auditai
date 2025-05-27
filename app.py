from dotenv import load_dotenv
from flask import Flask
from routes import main, ensinar,agentes,dashboard,revisao
from routes.extrair import bp_extrair

from database import db, configure_db
from models import Auditoria, Usuario, Agente, Diretriz

load_dotenv()

# Renomeado 'app' para 'application' para compatibilidade com Elastic Beanstalk
application = Flask(__name__) # <-- MUDANÇA AQUI
application.config['SECRET_KEY'] = 'sua_chave_ultra_secreta' # Altere para 'application'
configure_db(application) # <-- MUDANÇA AQUI
application.register_blueprint(main.bp) # <-- MUDANÇA AQUI
application.register_blueprint(ensinar.bp) # <-- MUDANÇA AQUI
application.register_blueprint(agentes.bp) # <-- MUDANÇA AQUI
application.register_blueprint(dashboard.bp) # <-- MUDANÇA AQUI
application.register_blueprint(revisao.bp) # <-- MUDANÇA AQUI
application.register_blueprint(bp_extrair) # <-- MUDANÇA AQUI


if __name__ == "__main__":
    # Modo debug deve ser desativado para produção
    application.run(debug=False) # <-- MUDANÇA AQUI (coloque False)