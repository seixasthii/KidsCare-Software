from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)
    
    # Configurações de sessão do Flask
    app.secret_key = app.config['SECRET_KEY']
    app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']

    # Registra as rotas da aplicação
    with app.app_context():
        from . import routes
        app.register_blueprint(routes.bp)

    return app
