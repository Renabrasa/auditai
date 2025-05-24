from flask import Flask
from routes import main, ensinar,agentes,dashboard,revisao
from routes.extrair import bp_extrair
from dotenv import load_dotenv
load_dotenv() # Carrega as variáveis do .env

app = Flask(__name__)
app.secret_key = "sua_chave_ultra_secreta"
app.register_blueprint(main.bp)
app.register_blueprint(ensinar.bp)
app.register_blueprint(agentes.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(revisao.bp)
app.register_blueprint(bp_extrair)


if __name__ == "__main__":
    app.run(debug=True)
