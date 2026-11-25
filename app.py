
from flask import Flask, render_template, request, redirect, flash
import os
import psycopg
from psycopg import IntegrityError
from dotenv import load_dotenv

# Carrega as informações do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Função para conectar ao banco PostgreSQL
def conectar_banco():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL não foi configurada.")

    conexao = psycopg.connect(database_url)
    return conexao



# Página inicial

@app.route("/")
def inicio():

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Busca todos os materiais
    cursor.execute("SELECT * FROM materiais")
    materiais = cursor.fetchall()

    # Conta os materiais cadastrados
    cursor.execute("""
        SELECT COUNT(*) FROM materiais
    """)
    total_materiais = cursor.fetchone()[0]

    # Soma todas as unidades disponíveis
    cursor.execute("""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM materiais
    """)
    estoque_disponivel = cursor.fetchone()[0]

    # Conta materiais com estoque baixo
    cursor.execute("""
        SELECT COUNT(*) FROM materiais
        WHERE quantidade > 0
        AND quantidade <= estoque_minimo
    """)
    estoque_baixo = cursor.fetchone()[0]

    # Conta materiais sem estoque
    cursor.execute("""
        SELECT COUNT(*) FROM materiais
        WHERE quantidade = 0
    """)
    estoque_critico = cursor.fetchone()[0]

    # Busca materiais que precisam de reposição
    cursor.execute("""
    SELECT * FROM materiais
    WHERE quantidade <= estoque_minimo
    ORDER BY quantidade ASC
    """)

    materiais_alerta = cursor.fetchall()

    # Busca as 5 movimentações mais recentes
    cursor.execute("""
    SELECT
        movimentacoes.codigo,
        materiais.nome,
        movimentacoes.tipo,
        movimentacoes.quantidade,
        movimentacoes.data_hora
    FROM movimentacoes
    LEFT JOIN materiais
    ON movimentacoes.codigo = materiais.codigo
    ORDER BY movimentacoes.id DESC
    LIMIT 5
    """)

    ultimas_movimentacoes = cursor.fetchall()

    conexao.close()

    return render_template(
        "index.html",
        materiais=materiais,
        total_materiais=total_materiais,
        estoque_disponivel=estoque_disponivel,
        estoque_baixo=estoque_baixo,
        estoque_critico=estoque_critico,
        materiais_alerta=materiais_alerta,
        ultimas_movimentacoes=ultimas_movimentacoes
    )


# Página de cadastro
@app.route("/cadastro")
def pagina_cadastro():
    return render_template("cadastro.html")


# Rota para cadastrar materiais

@app.route("/cadastrar", methods=["POST"])
def cadastrar():

    codigo = request.form["codigo"].strip()
    nome = request.form["nome"].strip()
    categoria = request.form["categoria"].strip()
    localizacao = request.form["localizacao"].strip()
    quantidade = int(request.form["quantidade"])
    estoque_minimo = int(request.form["estoque_minimo"])

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Verifica se o código já existe
    cursor.execute(
        "SELECT id FROM materiais WHERE codigo = %s",
        (codigo,)
    )

    material_existente = cursor.fetchone()

    if material_existente:
        conexao.close()
        flash("Já existe um material cadastrado com esse código.", "erro")
        return redirect("/cadastro")

    
    try:

        cursor.execute("""
            INSERT INTO materiais
            (codigo, nome, categoria, localizacao, quantidade, estoque_minimo)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            codigo,
            nome,
            categoria,
            localizacao,
            quantidade,
            estoque_minimo
        ))

        # Registra o cadastro no histórico de movimentações
        cursor.execute("""
            INSERT INTO movimentacoes
            (codigo, tipo, quantidade)
            VALUES (%s, %s, %s)
        """, (codigo, "Cadastro", quantidade))

        conexao.commit()

        flash("Material cadastrado com sucesso!", "sucesso")

    except IntegrityError:

        conexao.rollback()

        flash("Não foi possível cadastrar: esse código já existe.", "erro")

    conexao.close()

    return redirect("/cadastro")
    flash("Não foi possível cadastrar: esse código já existe.", "erro")

    conexao.close()

    return redirect("/cadastro")


# Página de consulta de materiais
@app.route("/consulta", methods=["GET"])
def consulta():

    busca = request.args.get("busca", "")
    categoria = request.args.get("categoria", "")
    situacao = request.args.get("situacao", "")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
    SELECT * FROM materiais
    WHERE (codigo LIKE %s OR nome LIKE %s)
    AND categoria LIKE %s
    AND (
        %s = ''
        OR (%s = 'critico' AND quantidade = 0)
        OR (%s = 'baixo' AND quantidade > 0 AND quantidade <= estoque_minimo)
        OR (%s = 'normal' AND quantidade > estoque_minimo)
    )
""", (
    f"%{busca}%",
    f"%{busca}%",
    f"%{categoria}%",
    situacao,
    situacao,
    situacao,
    situacao
))

    materiais = cursor.fetchall()

    # Busca as categorias cadastradas
    cursor.execute("""
        SELECT DISTINCT categoria
        FROM materiais
        WHERE categoria IS NOT NULL AND categoria != ''
        ORDER BY categoria
    """)

    categorias = cursor.fetchall()

    conexao.close()

    return render_template(
        "consulta.html",
        materiais=materiais,
        busca=busca,
        categorias=categorias,
        categoria_selecionada=categoria,
        situacao_selecionada=situacao
    )



@app.route("/editar/<int:id>")
def editar(id):

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT * FROM materiais WHERE id = %s",
        (id,)
    )

    material = cursor.fetchone()

    conexao.close()

    if material is None:
        flash("Material não encontrado.", "erro")
        return redirect("/consulta")

    return render_template("editar.html", material=material)



@app.route("/atualizar/<int:id>", methods=["POST"])
def atualizar(id):

    codigo = request.form["codigo"]
    nome = request.form["nome"]
    categoria = request.form["categoria"]
    localizacao = request.form["localizacao"]
    quantidade = int(request.form["quantidade"])
    estoque_minimo = int(request.form["estoque_minimo"])

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Busca o código e a quantidade anteriores
    cursor.execute("""
        SELECT codigo, quantidade
        FROM materiais
        WHERE id = %s
    """, (id,))

    material = cursor.fetchone()

    if material is None:
        conexao.close()
        flash("Material não encontrado.", "erro")
        return redirect("/consulta")

    codigo_antigo = material[0]
    quantidade_antiga = material[1]

    try:

        # Atualiza os dados do material
        cursor.execute("""
            UPDATE materiais
            SET codigo = %s,
                nome = %s,
                categoria = %s,
                localizacao = %s,
                quantidade = %s,
                estoque_minimo = %s
            WHERE id = %s
        """, (
            codigo,
            nome,
            categoria,
            localizacao,
            quantidade,
            estoque_minimo,
            id
        ))

        # Atualiza o código nas movimentações antigas
        if codigo != codigo_antigo:

            cursor.execute("""
                UPDATE movimentacoes
                SET codigo = %s
                WHERE codigo = %s
            """, (codigo, codigo_antigo))

        # Verifica se a quantidade foi alterada
        if quantidade != quantidade_antiga:

            diferenca = abs(quantidade - quantidade_antiga)

            cursor.execute("""
                INSERT INTO movimentacoes
                (codigo, tipo, quantidade)
                VALUES (%s, %s, %s)
            """, (codigo, "Ajuste", diferenca))

        conexao.commit()

        flash("Material atualizado com sucesso!", "sucesso")

    except IntegrityError:

        conexao.rollback()

        flash(
            "Esse código já está sendo utilizado por outro material.",
            "erro"
        )

    conexao.close()

    return redirect("/consulta")



@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Busca o código do material
    cursor.execute(
        "SELECT codigo FROM materiais WHERE id = %s",
        (id,)
    )

    material = cursor.fetchone()

    if material is None:
        conexao.close()
        flash("Material não encontrado.", "erro")
        return redirect("/consulta")

    codigo = material[0]

    # Verifica se existem movimentações desse material
    cursor.execute(
        "SELECT COUNT(*) FROM movimentacoes WHERE codigo = %s",
        (codigo,)
    )

    total_movimentacoes = cursor.fetchone()[0]

    if total_movimentacoes > 0:
        conexao.close()
        flash(
            "Não é possível excluir: este material possui movimentações no histórico.",
            "erro"
        )
        return redirect("/consulta")

    # Exclui o material
    cursor.execute(
        "DELETE FROM materiais WHERE id = %s",
        (id,)
    )

    conexao.commit()
    conexao.close()

    flash("Material excluído com sucesso!", "sucesso")

    return redirect("/consulta")


@app.route("/entrada")
def pagina_entrada():
    return render_template("entrada.html")




@app.route("/registrar_entrada", methods=["POST"])
def registrar_entrada():

    codigo = request.form["codigo"]
    quantidade = int(request.form["quantidade"])

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Verifica se o material existe
    cursor.execute(
        "SELECT quantidade FROM materiais WHERE codigo = %s",
        (codigo,)
    )

    material = cursor.fetchone()

    if material is None:
        conexao.close()
        flash("Material não encontrado. Confira o código.", "erro")
        return redirect("/entrada")

    # Atualiza o estoque
    cursor.execute("""
        UPDATE materiais
        SET quantidade = quantidade + %s
        WHERE codigo = %s
    """, (quantidade, codigo))

    # Registra a movimentação
    cursor.execute("""
        INSERT INTO movimentacoes (codigo, tipo, quantidade)
        VALUES (%s, %s, %s)
    """, (codigo, "Entrada", quantidade))

    conexao.commit()
    conexao.close()

    flash("Entrada de material registrada com sucesso!", "sucesso")

    return redirect("/entrada")

@app.route("/saida")
def pagina_saida():
    return render_template("saida.html")




@app.route("/registrar_saida", methods=["POST"])
def registrar_saida():

    codigo = request.form["codigo"]
    quantidade = int(request.form["quantidade"])

    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Verifica se o material existe
    cursor.execute(
        "SELECT quantidade FROM materiais WHERE codigo = %s",
        (codigo,)
    )

    material = cursor.fetchone()

    if material is None:
        conexao.close()
        flash("Material não encontrado. Confira o código.", "erro")
        return redirect("/saida")

    estoque_atual = material[0]

    # Verifica se existe quantidade suficiente
    if quantidade > estoque_atual:
        conexao.close()
        flash(
            f"Estoque insuficiente! Disponível: {estoque_atual} unidades.",
            "erro"
        )
        return redirect("/saida")

    # Atualiza o estoque
    cursor.execute("""
        UPDATE materiais
        SET quantidade = quantidade - %s
        WHERE codigo = %s
    """, (quantidade, codigo))

    # Registra a saída no histórico
    cursor.execute("""
        INSERT INTO movimentacoes (codigo, tipo, quantidade)
        VALUES (%s, %s, %s)
    """, (codigo, "Saída", quantidade))

    conexao.commit()
    conexao.close()

    flash("Saída de material registrada com sucesso!", "sucesso")

    return redirect("/saida")



@app.route("/historico")
def historico():

    conexao = conectar_banco()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT
            movimentacoes.id,
            movimentacoes.codigo,
            materiais.nome,
            movimentacoes.tipo,
            movimentacoes.quantidade,
            movimentacoes.data_hora
        FROM movimentacoes
        LEFT JOIN materiais
        ON movimentacoes.codigo = materiais.codigo
        ORDER BY movimentacoes.id DESC
    """)

    movimentacoes = cursor.fetchall()

    conexao.close()

    return render_template(
        "historico.html",
        movimentacoes=movimentacoes
    )




if __name__ == "__main__":
    app.run(debug=False)
