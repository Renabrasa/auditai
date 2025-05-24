from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return wrapper

def apenas_agente(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("usuario_tipo") != "agente":
            return redirect(url_for("main.usuarios"))  # ou outra página
        return f(*args, **kwargs)
    return wrapper

def apenas_supervisor(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("usuario_tipo") not in ["supervisor", "admin"]:
            return redirect(url_for("main.usuarios"))  # ou proibir acesso
        return f(*args, **kwargs)
    return wrapper
