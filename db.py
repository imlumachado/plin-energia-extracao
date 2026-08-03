
"""
Camada de persistência SQLite para as faturas PLIN.

Responsabilidades:
    - criar o schema (tabelas faturas e execucoes)
    - gravar faturas com upsert (sem duplicar ao rodar de novo)
    - registrar cada execução da coleta
    - oferecer consultas simples para o dashboard

Uso como script:
    python db.py <banco.sqlite> <faturas.json> [--novo]

Uso como módulo:
    import db
    resumo = db.gravar(faturas, "saida_plin/plin.db")
    faturas = db.consultar_todas("saida_plin/plin.db")
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from extracao import CAMPOS_FATURA


# =============================================================================
# SCHEMA
# =============================================================================

COLUNAS_FATURA = CAMPOS_FATURA + ["coletado_em"]

SQL_CRIAR_FATURAS = """
CREATE TABLE IF NOT EXISTS faturas (
    uc TEXT,
    cnpj TEXT,
    razao_social TEXT,
    endereco TEXT,
    competencia TEXT,
    dealership_bill_id TEXT PRIMARY KEY,
    bill_external_ref TEXT,
    date_ref TEXT,
    date_due TEXT,
    bill_date_due TEXT,
    kwh_consumed REAL,
    kwh_compensado REAL,
    consumption_flag TEXT,
    dealership_bill_cost REAL,
    dealership_extra_fees REAL,
    dealership_energy_cost REAL,
    dealership_energy_cost_without_plin REAL,
    bill_cost REAL,
    saved_money REAL,
    saved_co2_kg REAL,
    saved_trees REAL,
    desconto REAL,
    desconto_final REAL,
    desconto_uc REAL,
    dealership_bill_status TEXT,
    bill_status TEXT,
    scraper_status TEXT,
    bill_pdf_url TEXT,
    data_pagamento TEXT,
    paid_amount REAL,
    left_amount REAL,
    tem_boleto_plin INTEGER,
    energy_read_id TEXT,
    energy_bill_id TEXT,
    company_id TEXT,
    checking_account_id TEXT,
    boleto_unico_uc INTEGER,
    file_key TEXT,
    date_payment TEXT,
    proxima_leitura TEXT,
    coletado_em TEXT
)
"""

SQL_CRIAR_EXECUCOES = """
CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_execucao TEXT NOT NULL,
    quantidade_faturas INTEGER NOT NULL,
    quantidade_novas INTEGER NOT NULL,
    quantidade_atualizadas INTEGER NOT NULL,
    status TEXT NOT NULL,
    detalhe TEXT
)
"""

SQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_faturas_uc ON faturas(uc)",
    "CREATE INDEX IF NOT EXISTS idx_faturas_competencia ON faturas(competencia)",
    "CREATE INDEX IF NOT EXISTS idx_faturas_status ON faturas(bill_status)",
]

SQL_UPSERT_FATURA = f"""
INSERT INTO faturas (
    {", ".join(COLUNAS_FATURA)}
) VALUES (
    {", ".join(":" + c for c in COLUNAS_FATURA)}
)
ON CONFLICT(dealership_bill_id) DO UPDATE SET
    {", ".join(f"{c} = excluded.{c}" for c in COLUNAS_FATURA if c != "dealership_bill_id")}
"""


# =============================================================================
# CONEXÃO E SCHEMA
# =============================================================================

def conectar(caminho):
    caminho = Path(caminho)

    caminho.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        caminho,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def criar_schema(conn):
    conn.execute(SQL_CRIAR_FATURAS)
    conn.execute(SQL_CRIAR_EXECUCOES)

    for sql in SQL_INDEXES:
        conn.execute(sql)

    conn.commit()


# =============================================================================
# NORMALIZAÇÃO PARA O BANCO
# =============================================================================

def _preparar_fatura(fatura, coletado_em):
    linha = {}

    for campo in COLUNAS_FATURA:
        valor = fatura.get(campo)

        if campo in {
            "tem_boleto_plin",
            "boleto_unico_uc",
        }:
            valor = 1 if valor else 0

        linha[campo] = valor

    linha["coletado_em"] = coletado_em

    return linha


# =============================================================================
# GRAVAÇÃO
# =============================================================================

def upsert_faturas(conn, faturas, coletado_em=None):
    """
    Grava faturas com upsert pela dealership_bill_id.

    Retorna (novas, atualizadas).
    """
    if coletado_em is None:
        coletado_em = datetime.now().isoformat()

    ids_existentes = set(
        linha[0]
        for linha in conn.execute(
            "SELECT dealership_bill_id FROM faturas"
        )
    )

    ids_batch = {
        f["dealership_bill_id"]
        for f in faturas
        if f.get("dealership_bill_id")
    }

    novas = len(ids_batch - ids_existentes)

    conn.execute("BEGIN")

    for fatura in faturas:
        if not fatura.get("dealership_bill_id"):
            continue

        linha = _preparar_fatura(
            fatura,
            coletado_em
        )

        conn.execute(
            SQL_UPSERT_FATURA,
            linha
        )

    conn.commit()

    atualizadas = len(faturas) - novas

    return novas, atualizadas


def registrar_execucao(
    conn,
    quantidade_faturas,
    novas,
    atualizadas,
    status="SUCESSO",
    detalhe=None,
):
    conn.execute(
        """
        INSERT INTO execucoes (
            data_execucao,
            quantidade_faturas,
            quantidade_novas,
            quantidade_atualizadas,
            status,
            detalhe
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            quantidade_faturas,
            novas,
            atualizadas,
            status,
            detalhe,
        ),
    )

    conn.commit()


def gravar(
    faturas,
    caminho_db="saida_plin/plin.db",
    status="SUCESSO",
    detalhe=None,
):
    """
    Fluxo completo: conecta, cria schema, faz upsert e registra execução.

    Retorna um dicionário com o resumo da gravação.
    """
    conn = conectar(caminho_db)

    try:
        criar_schema(conn)

        novas, atualizadas = upsert_faturas(
            conn,
            faturas
        )

        registrar_execucao(
            conn,
            quantidade_faturas=len(faturas),
            novas=novas,
            atualizadas=atualizadas,
            status=status,
            detalhe=detalhe,
        )

        resumo = {
            "quantidade_faturas": len(faturas),
            "novas": novas,
            "atualizadas": atualizadas,
            "banco": str(Path(caminho_db)),
        }

        print(
            f"[BANCO] {resumo['banco']} "
            f"- {len(faturas)} faturas "
            f"({novas} novas, {atualizadas} atualizadas)"
        )

        return resumo

    finally:
        conn.close()


# =============================================================================
# CONSULTAS
# =============================================================================

def consultar_todas(caminho_db="saida_plin/plin.db"):
    conn = conectar(caminho_db)

    try:
        linhas = conn.execute(
            "SELECT * FROM faturas ORDER BY uc, competencia"
        ).fetchall()

        return [
            dict(linha)
            for linha in linhas
        ]

    finally:
        conn.close()


def consultar_ultimas_execucoes(
    caminho_db="saida_plin/plin.db",
    limite=10,
):
    conn = conectar(caminho_db)

    try:
        linhas = conn.execute(
            """
            SELECT * FROM execucoes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()

        return [
            dict(linha)
            for linha in linhas
        ]

    finally:
        conn.close()


# =============================================================================
# MAIN (script autônomo)
# =============================================================================

def main():
    if len(sys.argv) < 3:
        print(
            "Uso: python db.py <banco.sqlite> <faturas.json>"
        )
        sys.exit(1)

    caminho_db = sys.argv[1]
    caminho_json = Path(sys.argv[2])

    with open(
        caminho_json,
        encoding="utf-8"
    ) as arquivo:

        faturas = json.load(arquivo)

    gravar(
        faturas,
        caminho_db,
    )

    total = len(
        consultar_todas(caminho_db)
    )

    print(
        f"Total de faturas no banco: {total}"
    )


if __name__ == "__main__":
    main()
