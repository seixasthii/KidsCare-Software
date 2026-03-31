import os
from datetime import timedelta
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "uma-chave-muito-segura-e-secreta")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "token-padrao-seguro")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    DEBUG = os.getenv("DEBUG", "True") == "True"
