from dotenv import load_dotenv
from flask import Flask
from routes import main, ensinar,agentes,dashboard,revisao
from routes.extrair import bp_extrair

from database import db, configure_db
from models import Auditoria, Usuario, Agente, Diretriz # Importe todos os seus modelos aqui

load_dotenv() # Carrega as variáveis do .env

# Renomeado 'app' para 'application' para compatibilidade com Elastic Beanstalk
application = Flask(__name__) # <-- ALTERE AQUI: de 'app' para 'application'
#application.secret_key = "sua_chave_ultra_secreta"
application.config['SECRET_KEY'] = 'sua_chave_ultra_secreta'
configure_db(application) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(main.bp) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(ensinar.bp) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(agentes.bp) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(dashboard.bp) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(revisao.bp) # <-- ALtere a chamada para usar 'application'
application.register_blueprint(bp_extrair) # <-- ALtere a chamada para usar 'application'

if __name__ == "__main__":
    # Modo debug deve ser desativado para produção
    application.run(debug=False) # <-- ALtere aqui para 'application' e debug=False