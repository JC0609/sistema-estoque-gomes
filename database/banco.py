
import sqlite3

# Conecta ao banco de dados
conexao = sqlite3.connect("database/estoque.db")

# Permite executar comandos SQL
cursor = conexao.cursor()

# Cria a tabela de materiais
cursor.execute("""
    CREATE TABLE IF NOT EXISTS materiais (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        categoria TEXT,
        localizacao TEXT,
        quantidade INTEGER DEFAULT 0,
        estoque_minimo INTEGER DEFAULT 0
    )
""")


cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")


# Salva as alterações
conexao.commit()

# Fecha a conexão
conexao.close()

print("Banco de dados criado com sucesso!")


