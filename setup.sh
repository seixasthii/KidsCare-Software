#!/bin/bash

echo "--------------------------------------------------"
echo "🚀 Iniciando Instalação Automática: KidsCare Clinic"
echo "--------------------------------------------------"

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null
then
    echo "❌ Erro: python3 não encontrado. Por favor, instale o Python."
    exit
fi

# 1. Criando o ambiente virtual (venv)
echo "📦 Criando ambiente virtual (venv)..."
python3 -m venv venv

# 2. Instalando as dependências
echo "📥 Instalando dependências (Flask, Supabase, Bcrypt, etc)..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install flask supabase bcrypt python-dotenv flask-cors

echo ""
echo "--------------------------------------------------"
echo "✅ TUDO PRONTO!"
echo "--------------------------------------------------"
echo "Para iniciar o servidor agora, use:"
echo "source venv/bin/activate && python app.py"
echo "--------------------------------------------------"
