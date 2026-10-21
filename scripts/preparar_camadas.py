"""Exporta mapas para publicação estática, sem alterar os dados de análise."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from shapely.geometry import MultiPolygon, mapping, shape
from shapely import make_valid

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "data" / "mapas"
MEIO_MUNDO = 20037508.342789244
ZOOM_MIN, ZOOM_MAX = 6, 12
CORES_VIGOR = {1: "#fa6970", 2: "#f7b47e", 3: "#44b160"}


def salvar_json(caminho, valor):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(valor, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def vetores(nome, campos):
    entrada = RAIZ / "data" / "mapas" / f"{nome}.geojson"
    dados = json.loads(entrada.read_text(encoding="utf-8-sig"))
    feicoes = []
    reparadas = 0
    for feicao in dados["features"]:
        geometria = shape(feicao["geometry"])
        if not geometria.is_valid:
            geometria = make_valid(geometria)
            reparadas += 1
        # Reparos podem gerar linhas/pontos residuais; a camada é de áreas.
        def poligonos(g):
            if g.geom_type == "Polygon":
                return [g]
            if hasattr(g, "geoms"):
                return [p for parte in g.geoms for p in poligonos(parte)]
            return []
        partes = poligonos(geometria)
        geometria = MultiPolygon(partes)
        geometria = geometria.simplify(0.0002, preserve_topology=True)
        if geometria.is_empty or not geometria.is_valid:
            raise ValueError(f"Geometria inválida em {nome}")
        if not (-180 <= geometria.bounds[0] <= geometria.bounds[2] <= 180
                and -90 <= geometria.bounds[1] <= geometria.bounds[3] <= 90):
            raise ValueError(f"Coordenadas incompatíveis com EPSG:4326 em {nome}")
        feicoes.append({
            "type": "Feature", "properties": {k: feicao["properties"].get(k) for k in campos},
            "geometry": mapping(geometria),
        })
    destino = SAIDA / f"{nome}.geojson"
    salvar_json(destino, {"type": "FeatureCollection", "features": feicoes})
    print(f"{nome}: {len(feicoes)} feições; {destino.stat().st_size / 1e6:.2f} MB", flush=True)
    return {"arquivo": destino.name, "origem": entrada.relative_to(RAIZ).as_posix(),
            "feicoes": len(feicoes), "simplificacao_graus": 0.0002,
            "geometrias_reparadas": reparadas, "campos": campos,
            "tratamento": "make_valid quando necessário; apenas componentes poligonais; simplificação com preservação de topologia por feição",
            "tamanho_bytes": destino.stat().st_size}


def raster():
    entrada = RAIZ / "data" / "mapbiomas" / "pasture_vigor-sp_classification_2025.tif"
    tiles = SAIDA / "mapbiomas"
    tiles.mkdir(parents=True, exist_ok=True)
    # PNG indexado: classe 0 transparente; classes 1–3 com as cores oficiais.
    paleta = [0] * 768
    for codigo, cor in CORES_VIGOR.items():
        paleta[codigo * 3:codigo * 3 + 3] = bytes.fromhex(cor[1:])
    disponiveis = []
    total_bytes = 0
    with rasterio.open(entrada) as origem:
        if origem.count != 1 or origem.nodata != 0:
            raise ValueError("Esperado raster de uma banda com NoData 0")
        oeste, sul, leste, norte = transform_bounds(origem.crs, "EPSG:4326", *origem.bounds)
        xmin, ymin, xmax, ymax = transform_bounds(origem.crs, "EPSG:3857", *origem.bounds)
        for z in range(ZOOM_MIN, ZOOM_MAX + 1):
            lado = 2 * MEIO_MUNDO / (2 ** z)
            resolucao = lado / 256
            x0, x1 = math.floor((xmin + MEIO_MUNDO) / lado), math.ceil((xmax + MEIO_MUNDO) / lado)
            y0, y1 = math.floor((MEIO_MUNDO - ymax) / lado), math.ceil((MEIO_MUNDO - ymin) / lado)
            grade = Affine(resolucao, 0, -MEIO_MUNDO + x0 * lado,
                           0, -resolucao, MEIO_MUNDO - y0 * lado)
            with WarpedVRT(origem, crs="EPSG:3857", transform=grade,
                           width=(x1 - x0) * 256, height=(y1 - y0) * 256,
                           resampling=Resampling.nearest, nodata=0) as vrt:
                # Lê uma linha de tiles por vez para manter o uso de memória limitado.
                for y in range(y0, y1):
                    linha = vrt.read(1, window=Window(0, (y - y0) * 256, vrt.width, 256))
                    if not set(np.unique(linha).tolist()).issubset({0, 1, 2, 3}):
                        raise ValueError("Classe de vigor inesperada")
                    for x in range(x0, x1):
                        dados = linha[:, (x - x0) * 256:(x - x0 + 1) * 256]
                        if not np.any(dados):
                            continue
                        chave = f"{z}/{x}/{y}"
                        caminho = tiles / f"{chave}.png"
                        caminho.parent.mkdir(parents=True, exist_ok=True)
                        imagem = Image.fromarray(dados).convert("P")
                        imagem.putpalette(paleta)
                        imagem.save(caminho, transparency=0, optimize=True)
                        disponiveis.append(chave)
                        total_bytes += caminho.stat().st_size
            print(f"MapBiomas: zoom {z} concluído; {len(disponiveis)} tiles acumulados", flush=True)
    return {"origem": entrada.relative_to(RAIZ).as_posix(),
            "url": "mapbiomas/{z}/{x}/{y}.png", "tiles": disponiveis,
            "bounds": [[sul, oeste], [norte, leste]],
            "min_zoom": ZOOM_MIN, "max_native_zoom": ZOOM_MAX,
            "crs": "EPSG:3857", "reamostragem": "nearest", "nodata": 0,
            "cores": CORES_VIGOR, "tamanho_bytes": total_bytes,
            "uso": "Somente visualização; cálculos devem usar o GeoTIFF de análise."}


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    regioes = vetores("RegiaoEcologica", ["id", "nomeRegiaoEco"])
    fito = vetores("RegiaoEcoFito", ["id", "idRegiaoEco", "nomeRegiaoEco",
                                    "idFitoFisionomia", "descFitofisionomia"])
    vigor = raster()
    salvar_json(SAIDA / "camadas.json", {
        "versao_schema": 1, "gerado_em": datetime.now(timezone.utc).isoformat(),
        "regioes": regioes, "fitofisionomias": fito, "mapbiomas": vigor,
    })
    print("Camadas exportadas para docs/data/mapas/", flush=True)


if __name__ == "__main__":
    main()
