"""Exporta somente agregados da última execução completa para o dashboard."""
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/processados/reservas_legais"
CAMPOS = ["pastagem_baixo_ha", "pastagem_medio_ha", "pastagem_alto_ha"]


def main():
    ultima = json.loads((BASE / "ultima_execucao.json").read_text(encoding="utf-8"))
    pasta = BASE / ultima["execucao"]
    with sqlite3.connect(f"{(pasta / 'reservas.sqlite').as_uri()}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        registros = [dict(r) for r in db.execute(
            "SELECT regiao_id, fito_id, ind_status, des_condic, n_reservas, " + ", ".join(CAMPOS) +
            " FROM agregado_regiao_fito_status_condicao ORDER BY regiao_id, fito_id, ind_status, des_condic"
        )]
    for r in registros:
        for chave in ("regiao_id", "fito_id"):
            if r[chave] is not None:
                r[chave] = str(r[chave])
        if any(not math.isfinite(r[c]) or r[c] < 0 for c in CAMPOS):
            raise ValueError("Área inválida no agregado")
    assert sum(r["n_reservas"] for r in registros) == ultima["total"]["n_reservas"]
    for campo in CAMPOS:
        assert math.isclose(sum(r[campo] for r in registros), ultima["total"][campo], abs_tol=1e-6)
    dados = dict(versao_schema=2, unidade="ha", execucao=ultima["execucao"],
                 calculado_em=ultima["concluido_em"], controles=ultima["controles"],
                 total=ultima["total"], registros=registros)
    destino = ROOT / "docs/data/areas_reservas_legais.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{destino}: {len(registros)} grupos; totais conferidos.")


if __name__ == "__main__":
    main()
