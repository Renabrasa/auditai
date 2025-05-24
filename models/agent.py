# models/agent.py
from app import db

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    supervisor = db.Column(db.String(120), nullable=True)
    equipe = db.Column(db.String(120), nullable=True)
