
import sqlite3
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

# Abre o banco local
banco_local = sqlite3.connect("database/estoque.db")
cursor_local = banco_local.cursor()

try:
    # Conecta ao Supabase
    conexao_nuvem = psycopg.connect(os.getenv("DATABASE_URL"))
    cursor_nuvem = conexao_nuvem.cursor()

    # Impede duplicar dados caso a migração já tenha sido feita
    cursor_nuvem.execute("SELECT COUNT(*) FROM materiais")
    if cursor_nuvem.fetchone()[0] > 0:
        raise Exception(
            "O banco da nuvem já possui materiais. "
            "Migração cancelada para proteger os dados."
        )

    cursor_nuvem.execute("SELECT COUNT(*) FROM movimentacoes")
    if cursor_nuvem.fetchone()[0] > 0:
        raise Exception(
            "O banco da nuvem já possui movimentações. "
            "Migração cancelada para proteger os dados."
        )

    # Busca os materiais do banco local
    cursor_local.execute("SELECT * FROM materiais")
    materiais = cursor_local.fetchall()

    # Transfere os materiais
    cursor_nuvem.executemany("""
        INSERT INTO materiais
        (id, codigo, nome, categoria, localizacao,
         quantidade, estoque_minimo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, materiais)

    # Busca o histórico do banco local
    cursor_local.execute("SELECT * FROM movimentacoes")
    movimentacoes = cursor_local.fetchall()

    # Transfere as movimentações
    cursor_nuvem.executemany("""
        INSERT INTO movimentacoes
        (id, codigo, tipo, quantidade, data_hora)
        VALUES (%s, %s, %s, %s, %s)
    """, movimentacoes)

    # Ajusta os identificadores automáticos
    for tabela in ("materiais", "movimentacoes"):
        cursor_nuvem.execute(f"""
            SELECT setval(
                pg_get_serial_sequence('public.{tabela}', 'id'),
                COALESCE((SELECT MAX(id) FROM public.{tabela}), 1),
                EXISTS (SELECT 1 FROM public.{tabela})
            )
        """)

    conexao_nuvem.commit()

    print("Migração concluída com sucesso!")
    print("Materiais transferidos:", len(materiais))
    print("Movimentações transferidas:", len(movimentacoes))

except Exception as erro:
    if "conexao_nuvem" in locals():
        conexao_nuvem.rollback()

    print("Erro na migração:", erro)

finally:
    banco_local.close()

    if "conexao_nuvem" in locals():
        conexao_nuvem.close()
