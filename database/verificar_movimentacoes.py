
import sqlite3

conexao = sqlite3.connect("database/estoque.db")
cursor = conexao.cursor()

cursor.execute("SELECT * FROM movimentacoes")

movimentacoes = cursor.fetchall()

print("HISTÓRICO DE MOVIMENTAÇÕES:")

for movimentacao in movimentacoes:
    print(movimentacao)

conexao.close()
