
import os
import psycopg
from dotenv import load_dotenv

# Carrega as configurações do arquivo .env
load_dotenv()

try:
    conexao = psycopg.connect(os.getenv("DATABASE_URL"))

    cursor = conexao.cursor()
    cursor.execute("SELECT current_database()")

    resultado = cursor.fetchone()

    print("Conexão com Supabase realizada com sucesso!")
    print("Banco conectado:", resultado[0])

    cursor.close()
    conexao.close()

except Exception as erro:
    print("Não foi possível conectar ao Supabase.")
    print("Erro:", erro)
