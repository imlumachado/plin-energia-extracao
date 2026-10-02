
"""
Pega as faturas PLIN do payload RSC e junta tudo numa coisa só.

O portal (Next.js) injeta os dados em blocos `self.__next_f.push([1, "..."])`.
Dentro deles os dados vêm deduplicados no formato "flight": cada objeto é
uma linha `<id>:<json>` e os campos repetidos viram `"$25"`. Então primeiro
a gente junta os blocos, indexa as linhas e resolve as referências. Depois
percorre a hierarquia:

    ucs[N]                                   <- unidade consumidora
    └── energy_reads[M]                      <- fatura da concessionária
        └── energy_bills[0]                  <- boleto PLIN (economia)

Antes o código achatava cada dicionário num registro separado, o que
"quebrava" cada fatura em 2 linhas. Aqui a gente percorre a hierarquia e
monta UMA fatura completa por energy_read, juntando os dados do boleto.

O portal também parou de enviar `dealership_bill_id`; a gente reconstrói a
mesma chave (`<uc>.<mês>.<ano>`) a partir do `date_ref`, que é o que segura
a deduplicação no banco.

Ligação: energy_bills[0].energy_read_id == energy_read.id
(conferida: 734/734 boletos vinculados).

Como script:
    python extracao.py <arquivo_html_ou_rsc> [saida.json]

Como módulo:
    from extracao import extrair_faturas
    faturas = extrair_faturas(html)
"""

import csv
import json
import re
import sys
from pathlib import Path


# =============================================================================
# CAMPOS DO MODELO UNIFICADO
# =============================================================================

CAMPOS_FATURA = [
    "uc",
    "cnpj",
    "razao_social",
    "endereco",
    "competencia",

    "dealership_bill_id",
    "bill_external_ref",

    "date_ref",
    "date_due",
    "bill_date_due",

    "kwh_consumed",
    "kwh_compensado",
    "consumption_flag",

    "dealership_bill_cost",
    "dealership_extra_fees",
    "dealership_energy_cost",
    "dealership_energy_cost_without_plin",

    "bill_cost",
    "saved_money",
    "saved_co2_kg",
    "saved_trees",

    "desconto",
    "desconto_final",
    "desconto_uc",

    "dealership_bill_status",
    "bill_status",
    "scraper_status",

    "bill_pdf_url",
    "data_pagamento",
    "paid_amount",
    "left_amount",

    "tem_boleto_plin",

    "energy_read_id",
    "energy_bill_id",
    "company_id",
    "checking_account_id",
    "boleto_unico_uc",
    "file_key",
    "date_payment",
    "proxima_leitura",
]

CAMPOS_NUMERICOS = {
    "kwh_consumed",
    "kwh_compensado",
    "dealership_bill_cost",
    "dealership_extra_fees",
    "dealership_energy_cost",
    "dealership_energy_cost_without_plin",
    "bill_cost",
    "saved_money",
    "saved_co2_kg",
    "saved_trees",
    "desconto",
    "desconto_final",
    "desconto_uc",
    "paid_amount",
    "left_amount",
}


# =============================================================================
# UTILIDADES
# =============================================================================

def converter_numero(valor):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return valor
    try:
        return float(valor)
    except Exception:
        return None


def normalizar_fatura(fatura):
    novo = {}
    for campo in CAMPOS_FATURA:
        valor = fatura.get(campo)
        if campo in CAMPOS_NUMERICOS:
            valor = converter_numero(valor)
        novo[campo] = valor
    return novo


# =============================================================================
# PAYLOAD DO NEXT.JS (FLIGHT)
# =============================================================================

RE_BLOCO_RSC = re.compile(
    r'self\.__next_f\.push\(\[1,\s*("(?:[^"\\]|\\.)*")\]\)',
    re.DOTALL
)

RE_LINHA_FLIGHT = re.compile(
    r"(?:^|\n)([0-9a-fA-F]+):"
)

RE_REFERENCIA = re.compile(
    r"^\$([0-9a-fA-F]+)"
)


def juntar_payload_rsc(texto):
    """Junta, num texto só, o conteúdo de cada bloco self.__next_f.push."""
    partes = []

    for bruto in RE_BLOCO_RSC.findall(texto):
        try:
            partes.append(json.loads(bruto))
        except Exception:
            continue

    return "".join(partes)


def indexar_blocos_flight(payload):
    """
    Mapeia as linhas `<id>:<json>` do payload em um dicionário.

    O Next.js deduplica o payload: cada objeto vira uma linha e os campos
    repetidos viram `"$25"`. Sem esse índice não dá para resolver nada.
    """
    marcadores = list(RE_LINHA_FLIGHT.finditer(payload))
    blocos = {}

    for posicao, marcador in enumerate(marcadores):
        inicio = marcador.end()
        fim = (
            marcadores[posicao + 1].start()
            if posicao + 1 < len(marcadores)
            else len(payload)
        )

        corpo = payload[inicio:fim].strip()

        if corpo[:1] not in ("{", "["):
            continue

        try:
            blocos[marcador.group(1)] = json.loads(corpo)
        except Exception:
            continue

    return blocos


def resolver_referencias(valor, blocos, cache=None, pilha=frozenset()):
    """
    Troca as referências `$id` do payload pelos objetos que elas apontam.

    Sem isso `energy_reads` chega como a string `"$25"` e nenhuma fatura é
    montada. O cache evita repetir o trabalho nos objetos compartilhados
    (conta de pagamento, concessionária, etc.).
    """
    if cache is None:
        cache = {}

    if isinstance(valor, str):
        referencia = RE_REFERENCIA.match(valor)

        if not referencia:
            return valor

        chave = referencia.group(1)

        if chave in cache:
            return cache[chave]

        if chave in pilha:
            return None

        cache[chave] = None

        resolvido = resolver_referencias(
            blocos.get(chave),
            blocos,
            cache,
            pilha | {chave}
        )

        cache[chave] = resolvido

        return resolvido

    if isinstance(valor, list):
        return [
            resolver_referencias(item, blocos, cache, pilha)
            for item in valor
        ]

    if isinstance(valor, dict):
        return {
            chave: resolver_referencias(
                item,
                blocos,
                cache,
                pilha
            )
            for chave, item in valor.items()
        }

    return valor


def extrair_objetos_balanceados(texto):
    """Pega todos os objetos JSON `{...}` balanceados de um texto."""
    objetos = []

    inicio = None
    profundidade = 0
    dentro_string = False
    escape = False

    for i, char in enumerate(texto):
        if dentro_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                dentro_string = False
            continue

        if char == '"':
            dentro_string = True
            continue

        if char == "{":
            if profundidade == 0:
                inicio = i
            profundidade += 1

        elif char == "}":
            if profundidade > 0:
                profundidade -= 1
                if profundidade == 0 and inicio is not None:
                    objeto = texto[inicio:i + 1]
                    if len(objeto) > 20:
                        objetos.append(objeto)
                    inicio = None

    return objetos


# =============================================================================
# PERCURSO DA HIERARQUIA
# =============================================================================

def _campos_uc(objeto):
    return {
        "uc": objeto.get("uc"),
        "cnpj": objeto.get("cnpj"),
        "razao_social": objeto.get("razao_social"),
        "endereco": objeto.get("endereco"),
        "desconto_uc": objeto.get("desconto"),
        "boleto_unico_uc": objeto.get("boleto_unico"),
        "checking_account_id": objeto.get("checking_account_id"),
    }


def _campos_energy_read(energy_read):
    return {
        "energy_read_id": energy_read.get("id"),
        "dealership_bill_id": energy_read.get("dealership_bill_id"),
        "date_ref": energy_read.get("date_ref"),
        "date_due": energy_read.get("date_due"),
        "date_payment": energy_read.get("date_payment"),
        "proxima_leitura": energy_read.get("proxima_leitura"),
        "kwh_consumed": energy_read.get("kwh_consumed"),
        "kwh_compensado": energy_read.get("kwh_compensado"),
        "dealership_bill_cost": energy_read.get("dealership_bill_cost"),
        "dealership_extra_fees": energy_read.get("dealership_extra_fees"),
        "dealership_bill_status": energy_read.get("dealership_bill_status"),
        "scraper_status": energy_read.get("scraper_status"),
        "file_key": energy_read.get("file_key"),
    }

def _campos_energy_bill(bill):
    return {
        "bill_external_ref": bill.get("bill_external_ref"),
        "bill_cost": bill.get("bill_cost"),
        "bill_date_due": bill.get("bill_date_due"),
        "bill_status": bill.get("bill_status"),
        "bill_pdf_url": bill.get("bill_pdf_url"),
        "saved_money": bill.get("saved_money"),
        "saved_co2_kg": bill.get("saved_co2_kg"),
        "saved_trees": bill.get("saved_trees"),
        "consumption_flag": bill.get("consumption_flag"),
        "dealership_energy_cost": bill.get("dealership_energy_cost"),
        "dealership_energy_cost_without_plin": (
            bill.get("dealership_energy_cost_without_plin_estimation")
        ),
        "desconto": bill.get("desconto"),
        "desconto_final": bill.get("desconto_final"),
        "company_id": bill.get("company_id"),
        "data_pagamento": bill.get("data_pagamento"),
        "paid_amount": bill.get("paid_amount"),
        "left_amount": bill.get("left_amount"),
        "energy_bill_id": bill.get("id"),
    }


def _eh_placeholder(fatura):
    """
    Descarta as faturas placeholder do tipo `UC.1.1970` (PENDING, sem dados).
    """
    dealership_bill_id = fatura.get("dealership_bill_id") or ""
    if "1.1970" in str(dealership_bill_id):
        return True

    competencia = fatura.get("competencia") or ""
    if competencia == "1970-01":
        return True

    return False


# =============================================================================
# EXTRAÇÃO PRINCIPAL
# =============================================================================

def _montar_chave_fatura(fatura):
    """
    Monta a chave `<uc>.<mês>.<ano>` que o portal usava como identificador.

    O portal parou de mandar `dealership_bill_id`, mas a chave continua
    valendo: é ela que impede o banco de duplicar a fatura a cada extração.
    """
    date_ref = fatura.get("date_ref") or ""

    if len(date_ref) < 7:
        return None

    if not (date_ref[:4].isdigit() and date_ref[5:7].isdigit()):
        return None

    return (
        f"{fatura.get('uc')}."
        f"{int(date_ref[5:7])}."
        f"{int(date_ref[:4])}"
    )


def _registrar_faturas(uc, faturas, vistos):
    """Junta as faturas de uma UC, uma por energy_read."""
    uc_info = _campos_uc(uc)

    for energy_read in uc.get("energy_reads") or []:
        if not isinstance(energy_read, dict):
            continue

        energy_read_id = energy_read.get("id")

        if energy_read_id in vistos:
            continue

        vistos.add(energy_read_id)

        fatura = _campos_energy_read(energy_read)
        fatura.update(uc_info)

        bills = energy_read.get("energy_bills") or []

        if isinstance(bills, list) and bills:
            fatura.update(
                _campos_energy_bill(bills[0])
            )
            fatura["tem_boleto_plin"] = True
        else:
            fatura["tem_boleto_plin"] = False

        fatura["competencia"] = (
            (fatura.get("date_ref") or "")[:7]
        )

        fatura["dealership_bill_id"] = (
            fatura.get("dealership_bill_id")
            or _montar_chave_fatura(fatura)
        )

        if _eh_placeholder(fatura):
            continue

        faturas.append(
            normalizar_fatura(fatura)
        )


def extrair_faturas(texto_rsc):
    """
    Junta as faturas a partir do payload do portal.

    Devolve uma lista de dicionários (um por energy_read), já com os dados
    do boleto PLIN. Placeholders (1970) são descartados e duplicatas do
    mesmo energy_read (render mobile/desktop) são removidas.
    """
    faturas = []
    vistos = set()

    payload = juntar_payload_rsc(texto_rsc)
    blocos = indexar_blocos_flight(payload)

    cache = {}

    def resolver(valor):
        return resolver_referencias(
            valor,
            blocos,
            cache
        )

    pilha = list(blocos.values())

    while pilha:
        atual = pilha.pop()

        if isinstance(atual, dict):
            if "uc" in atual and "energy_reads" in atual:
                _registrar_faturas(
                    resolver(atual),
                    faturas,
                    vistos
                )
            else:
                pilha.extend(atual.values())

        elif isinstance(atual, list):
            pilha.extend(atual)

    # formato antigo: hierarquia embutida no HTML, sem índices do flight
    if not faturas:
        for objeto_texto in extrair_objetos_balanceados(payload):
            try:
                dados = json.loads(objeto_texto)
            except Exception:
                continue

            pilha = [dados]

            while pilha:
                atual = pilha.pop()

                if isinstance(atual, dict):
                    if "uc" in atual and isinstance(
                        atual.get("energy_reads"),
                        list
                    ):
                        _registrar_faturas(
                            atual,
                            faturas,
                            vistos
                        )

                    pilha.extend(atual.values())

                elif isinstance(atual, list):
                    pilha.extend(atual)

    return faturas


# =============================================================================
# EXPORTAÇÃO
# =============================================================================

def salvar_json(faturas, caminho):
    caminho = Path(caminho)

    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(
            faturas,
            arquivo,
            ensure_ascii=False,
            indent=2,
            default=str
        )

    print(f"JSON: {caminho}")


def salvar_csv(faturas, caminho):
    caminho = Path(caminho)

    campos = list(CAMPOS_FATURA)
    campos += [c for c in faturas[0].keys() if c not in campos] if faturas else []

    with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
        writer = csv.DictWriter(
            arquivo,
            fieldnames=campos,
            extrasaction="ignore"
        )
        writer.writeheader()

        for fatura in faturas:
            writer.writerow(fatura)

    print(f"CSV: {caminho}")


# =============================================================================
# MAIN (script autônomo)
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("Uso: python extracao.py <arquivo_html_ou_rsc> [saida.json]")
        sys.exit(1)

    entrada = Path(sys.argv[1])

    saida = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else entrada.parent / "faturas_unificadas.json"
    )

    texto = entrada.read_text(encoding="utf-8")

    faturas = extrair_faturas(texto)

    print(f"Faturas unificadas: {len(faturas)}")
    print(
        f"Com boleto PLIN: "
        f"{sum(1 for f in faturas if f['tem_boleto_plin'])}"
    )
    print(
        f"Sem boleto PLIN: "
        f"{sum(1 for f in faturas if not f['tem_boleto_plin'])}"
    )
    print(
        f"UCs distintas: "
        f"{len({f['uc'] for f in faturas})}"
    )

    competencias = sorted({
        f["competencia"]
        for f in faturas
        if f["competencia"] and f["competencia"] != "1970-01"
    })

    if competencias:
        print(
            f"Competências: {competencias[0]} a {competencias[-1]}"
        )

    salvar_json(faturas, saida)

    csv_saida = saida.with_suffix(".csv")
    if faturas:
        salvar_csv(faturas, csv_saida)


if __name__ == "__main__":
    main()
