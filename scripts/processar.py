"""Gera o contrato inicial de dados do dashboard, sem resultados simulados."""

import json
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "data" / "resultados.json"


def main():
    resultados = {
        "versao_schema": 1,
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "status": "aguardando_dados",
        "mensagem": "Os indicadores financeiros serão calculados após a definição das premissas dos cenários.",
        "unidades": {"area": "ha", "moeda": "BRL"},
        "premissas": {
            "ano_referencia": None,
            "taxa_desconto_anual": None,
            "percentuais_recuperacao": [],
        },
        "indicadores": {
            "area_degradada_ha": None,
            "area_recuperada_ha": None,
            "investimento_brl": None,
        },
        "regioes": [],
        "cenarios": [],
        "mapas": [],
        "fontes": [],
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Resultados gerados em: {SAIDA}")


if __name__ == "__main__":
    main()
