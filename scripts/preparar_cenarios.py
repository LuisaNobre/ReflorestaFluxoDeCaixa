"""Pré-calcula área × valor por hectare por fluxo e categoria cadastral."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data"


def ler(nome):
    return json.loads((DATA / nome).read_text(encoding="utf-8"))


def main():
    catalogo = ler("filtros_cenarios.json")
    if any(r["InvNecessario"] < 0 for r in catalogo["registros"]):
        raise ValueError("Catálogo contém investimento negativo; execute preparar_filtros_cenarios.py")
    areas = ler("areas.json")
    config = ler("mapas/camadas.json")
    vetores = ler("mapas/" + config["fitofisionomias"]["arquivo"])
    tipos = {str(f["properties"]["id"]): str(f["properties"]["idFitoFisionomia"]) for f in vetores["features"]}
    regioes = {r["id"]: r["bit"] for r in areas["regioes"]}
    fitos = sorted(areas["fitos"], key=lambda f: int(f["id"]))
    hectares = defaultdict(float)
    sem_par = 0
    for r in areas["registros"]:
        if r["v"] != 1:
            continue
        candidatos = [f for f in fitos if int(r["f"]) & (1 << f["bit"])
                      and r["r"] & (1 << regioes[f["id_regiao"]])]
        if candidatos:
            f = candidatos[0]
            hectares[f["id_regiao"], tipos[f["id"]]] += r["ha"]
        else:
            sem_par += r["ha"]
    reservas = ler("areas_reservas_legais.json")
    rl = defaultdict(list)
    for r in reservas["registros"]:
        if r["fito_id"] in tipos and r["regiao_id"] is not None:
            rl[r["regiao_id"], tipos[r["fito_id"]]].append(r)
    vistos = set()
    for r in catalogo["registros"]:
        chave = tuple(r[c] for c in ["idRegiaoEco", "idFitofisionomia", "idFaixaTipo", "idTopografia", "idMecanizacaoNivel"])
        if chave in vistos:
            raise ValueError(f"Mais de um fluxo para {chave}; resolver antes de calcular")
        vistos.add(chave)
        par = chave[:2]
        def calcular(ha):
            return dict(area_ha=ha, vpl=ha * r["VPLiquido"], investimento=ha * r["InvNecessario"])
        r["cenario_total"] = calcular(hectares[par])
        r["cenario_rl"] = [dict(ind_status=a["ind_status"], des_condic=a["des_condic"],
                                 **calcular(a["pastagem_baixo_ha"])) for a in rl[par]]
    resultado = dict(versao_schema=1, fonte_excel=catalogo["fonte"],
                     execucao_rl=reservas["execucao"], area_baixo_sem_par_ha=sem_par,
                     areas=[dict(idRegiaoEco=k[0], idFitofisionomia=k[1], area_ha=v) for k,v in hectares.items()],
                     areas_rl=[dict(idRegiaoEco=k[0], idFitofisionomia=k[1],
                                    ind_status=a["ind_status"], des_condic=a["des_condic"],
                                    area_ha=a["pastagem_baixo_ha"]) for k, valores in rl.items() for a in valores],
                     registros=catalogo["registros"])
    (DATA / "cenarios.json").write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Cenários pré-calculados: {len(vistos)} fluxos; baixo vigor sem par: {sem_par:.2f} ha")


if __name__ == "__main__":
    main()
