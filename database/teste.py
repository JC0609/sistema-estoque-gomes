
import sqlite3

# Conecta ao banco de dados
conexao = sqlite3.connect("database/estoque.db")

cursor = conexao.cursor()

# Cadastra um material
cursor.execute("""
    INSERT OR IGNORE INTO materiais
    (codigo, nome, categoria, localizacao, quantidade, estoque_minimo)
    VALUES (?, ?, ?, ?, ?, ?)
""", ("MAT001", "Parafuso", "Fixadores", "A-01-02", 500, 100))

# Salva o cadastro
conexao.commit()

# Consulta os materiais cadastrados
cursor.execute("SELECT * FROM materiais")

materiais = cursor.fetchall()

# Mostra os resultados
for material in materiais:
    print(material)

# Fecha a conexão
conexao.close()
