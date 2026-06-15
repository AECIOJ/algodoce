"""initial_schema

Revision ID: 97608961c665
Revises: 
Create Date: 2026-05-16 18:28:57.892763

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '97608961c665'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(120) NOT NULL UNIQUE,
            telefone VARCHAR(20),
            endereco TEXT,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            preco NUMERIC(10, 2) NOT NULL,
            unidade VARCHAR(20) NOT NULL DEFAULT 'cento',
            imagem VARCHAR(255),
            ativo BOOLEAN DEFAULT TRUE
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            unidade_medida VARCHAR(20) NOT NULL
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS product_ingredients (
            product_id INTEGER NOT NULL REFERENCES products(id),
            ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
            quantidade NUMERIC(10, 3) NOT NULL,
            PRIMARY KEY (product_id, ingredient_id)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id),
            data_pedido TIMESTAMP NOT NULL DEFAULT NOW(),
            data_entrega DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pendente',
            observacao TEXT,
            total NUMERIC(10, 2)
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantidade NUMERIC(10, 3) NOT NULL,
            preco_unitario NUMERIC(10, 2) NOT NULL
        )
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS order_items")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS product_ingredients")
    op.execute("DROP TABLE IF EXISTS ingredients")
    op.execute("DROP TABLE IF EXISTS products")
    op.execute("DROP TABLE IF EXISTS clients")
