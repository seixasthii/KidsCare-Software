from supabase import create_client, Client
from config import Config

def get_supabase_client() -> Client:
    """Retorna uma instância única e configurada do cliente Supabase."""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL ou SUPABASE_KEY não configurados no .env")
    
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# Instância global para uso nas rotas
supabase = get_supabase_client()
