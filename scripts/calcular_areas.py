"""Pré-calcula áreas na grade original do MapBiomas, sem dupla contagem.

Cada registro contém a área de pixels com a mesma combinação de pertencimento
a regiões, fitofisionomias e classe de vigor. Essa partição permite agregar
qualquer seleção no HTML, inclusive onde os polígonos se sobrepõem.
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.features import rasterize
from rasterio.windows import Window, bounds as window_bounds
from shapely import make_valid
from shapely.geometry import box, mapping, shape
from shapely.strtree import STRtree

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "data" / "areas.json"
RASTER = RAIZ / "data" / "mapbiomas" / "pasture_vigor-sp_classification_2025.tif"
GEOD = Geod(ellps="WGS84")


def poligonos(geometria):
    if geometria.geom_type == "Polygon":
        yield geometria
    elif hasattr(geometria, "geoms"):
        for parte in geometria.geoms:
            yield from poligonos(parte)


def carregar(nome):
    caminho = RAIZ / "data" / "mapas" / f"{nome}.geojson"
    dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    resultado = []
    reparadas = 0
    for feicao in dados["features"]:
        geometria = shape(feicao["geometry"])
        if not geometria.is_valid:
            geometria = make_valid(geometria)
            reparadas += 1
        partes = list(poligonos(geometria))
        if not partes:
            raise ValueError(f"Feição sem área em {nome}")
        resultado.append((feicao["properties"], partes))
    print(f"{nome}: {len(resultado)} feições; {reparadas} reparos, sem simplificação", flush=True)
    return resultado, {"arquivo": caminho.relative_to(RAIZ).as_posix(),
                       "sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
                       "geometrias_reparadas": reparadas}


def areas_linhas(origem):
    """Área geodésica de um pixel por linha; constante ao longo da longitude."""
    t = origem.transform
    if origem.crs.to_epsg() != 4326 or t.b != 0 or t.d != 0 or t.a <= 0 or t.e >= 0:
        raise ValueError("Esperado raster EPSG:4326, sem rotação e orientado ao norte")
    areas = np.empty(origem.height, dtype="float64")
    for linha in range(origem.height):
        norte = t.f + linha * t.e
        sul = norte + t.e
        area, _ = GEOD.polygon_area_perimeter(
            [t.c, t.c + t.a, t.c + t.a, t.c], [norte, norte, sul, sul],
        )
        areas[linha] = abs(area) / 10000
    return areas


def main():
    regioes, fonte_regioes = carregar("RegiaoEcologica")
    fitos, fonte_fitos = carregar("RegiaoEcoFito")
    if len(regioes) > 6 or len(fitos) > 63:
        raise ValueError("Rever a codificação de pertencimento para esta quantidade de feições")
    ids_regioes = {str(p["id"]): p["nomeRegiaoEco"] for p, _ in regioes}
    if any(ids_regioes.get(str(p["idRegiaoEco"])) != p["nomeRegiaoEco"] for p, _ in fitos):
        raise ValueError("Hierarquia de regiões e fitofisionomias inconsistente")
    partes, proprietarios = [], []
    for grupo, feicoes in enumerate((regioes, fitos)):
        for indice, (_, geometrias) in enumerate(feicoes):
            for geometria in geometrias:
                partes.append(geometria)
                proprietarios.append((grupo, indice))
    arvore = STRtree(partes)
    geometrias = [mapping(p) for p in partes]
    totais = defaultdict(float)
    contagens = defaultdict(int)
    totais_vigor = np.zeros(4, dtype="float64")
    print(f"Índice espacial: {len(partes)} componentes poligonais", flush=True)
    with rasterio.open(RASTER) as origem:
        if origem.count != 1 or origem.nodata != 0:
            raise ValueError("Esperado vigor de uma banda e NoData 0")
        areas = areas_linhas(origem)
        # A extensão da grade deve conter inteiramente as duas bases vetoriais.
        if not all(box(*origem.bounds).covers(p) for p in partes):
            raise ValueError("A grade não contém todos os polígonos; ampliar a grade antes de calcular")
        linhas_totais = (origem.height + 2047) // 2048
        for faixa, linha in enumerate(range(0, origem.height, 2048), 1):
            for coluna in range(0, origem.width, 2048):
                janela = Window(coluna, linha, min(2048, origem.width - coluna), min(2048, origem.height - linha))
                vigor = origem.read(1, window=janela)
                if not set(np.unique(vigor).tolist()).issubset({0, 1, 2, 3}):
                    raise ValueError("Classes inesperadas no GeoTIFF")
                r = np.zeros(vigor.shape, dtype="uint8")
                f = np.zeros(vigor.shape, dtype="uint64")
                candidatos = defaultdict(list)
                for indice in arvore.query(box(*window_bounds(janela, origem.transform))):
                    candidatos[proprietarios[indice]].append(geometrias[indice])
                for (grupo, indice), formas in candidatos.items():
                    mascara = rasterize(((g, 1) for g in formas), out_shape=vigor.shape,
                                        transform=origem.window_transform(janela),
                                        fill=0, all_touched=False, dtype="uint8").astype(bool)
                    if grupo == 0:
                        r[mascara] |= np.uint8(1 << indice)
                    else:
                        f[mascara] |= np.uint64(1 << indice)
                # As chaves locais compactas tornam a agregação de pixels rápida.
                valores_f, inverso = np.unique(f, return_inverse=True)
                chaves = (inverso.reshape(vigor.shape).astype("uint32") << 8) | (r.astype("uint32") << 2) | vigor
                pesos = np.broadcast_to(areas[linha:linha + vigor.shape[0], None], vigor.shape).ravel()
                areas_chaves = np.bincount(chaves.ravel(), weights=pesos)
                pixels_chaves = np.bincount(chaves.ravel())
                for chave in np.flatnonzero(pixels_chaves):
                    key = ((int(chave) >> 2) & 63, int(valores_f[int(chave) >> 8]), int(chave) & 3)
                    if key == (0, 0, 0):
                        continue
                    totais[key] += float(areas_chaves[chave])
                    contagens[key] += int(pixels_chaves[chave])
                totais_vigor += np.bincount(vigor.ravel(), weights=pesos, minlength=4)
            print(f"Faixa {faixa}/{linhas_totais} concluída; {len(totais)} combinações", flush=True)
        metadados_grade = {"crs": str(origem.crs), "resolucao_graus": list(origem.res),
                           "dimensoes": [origem.width, origem.height], "bounds": list(origem.bounds),
                           "area_pixel_ha_min": float(areas.min()), "area_pixel_ha_max": float(areas.max())}
    registros = [{"r": r, "f": str(f), "v": v, "ha": round(area, 8), "pixels": contagens[r, f, v]}
                 for (r, f, v), area in sorted(totais.items())]
    for classe in (1, 2, 3):
        acumulado = sum(item["ha"] for item in registros if item["v"] == classe)
        if not np.isclose(acumulado, totais_vigor[classe], rtol=1e-9, atol=1e-4):
            raise ValueError("Partição territorial perdeu ou duplicou pixels de pastagem")
    resultado = {
        "versao_schema": 1, "gerado_em": datetime.now(timezone.utc).isoformat(), "unidade": "ha",
        "metodo": "Estimativa por centros de pixels na grade nativa, ponderados pela área geodésica WGS84 por linha. Sobreposições preservadas como pertencimento múltiplo e contadas uma vez por seleção. NoData excluído das pastagens, incluído nas áreas territoriais.",
        "fontes": [fonte_regioes, fonte_fitos, {"arquivo": RASTER.relative_to(RAIZ).as_posix(),
                    "sha256": hashlib.sha256(RASTER.read_bytes()).hexdigest()}],
        "grade": metadados_grade,
        "regioes": [{"id": str(p["id"]), "nome": p["nomeRegiaoEco"], "bit": i} for i, (p, _) in enumerate(regioes)],
        "fitos": [{"id": str(p["id"]), "id_regiao": str(p["idRegiaoEco"]),
                   "tipo": p["descFitofisionomia"], "bit": i} for i, (p, _) in enumerate(fitos)],
        "registros": registros,
        "controle_vigor_sp_ha": {str(c): round(float(totais_vigor[c]), 8) for c in (1, 2, 3)},
        "controle_pixels_vigor": {str(c): sum(item["pixels"] for item in registros if item["v"] == c) for c in (1, 2, 3)},
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    temporario = SAIDA.with_suffix(".tmp.json")
    temporario.write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporario.replace(SAIDA)
    print(f"Áreas salvas: {SAIDA} ({SAIDA.stat().st_size} bytes)", flush=True)
    print(json.dumps(resultado["controle_vigor_sp_ha"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
