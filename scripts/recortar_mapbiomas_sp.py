"""Recorta o raster original pelo limite oficial de SP, sem reamostragem."""

import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import rasterio
import shapefile
from rasterio.crs import CRS
from rasterio.features import geometry_mask, geometry_window
from rasterio.warp import transform_geom
from rasterio.windows import Window

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "data" / "mapbiomas"
ORIGINAL = PASTA / "pasture_vigor-brazil_classification_2025.tif"
SAIDA = PASTA / "pasture_vigor-sp_classification_2025.tif"
LIMITES = RAIZ / "data" / "mapas" / "limites"
ZIP = LIMITES / "SP_UF_2024.zip"
URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_UF_2024.zip"
)


def limite_sp():
    LIMITES.mkdir(parents=True, exist_ok=True)
    if not ZIP.exists():
        print("Baixando limite de São Paulo do IBGE…", flush=True)
        with urlopen(URL, timeout=120) as resposta:
            conteudo = resposta.read()
        # Valida o download antes de salvar o cache.
        with ZipFile(io.BytesIO(conteudo)) as arquivo:
            if arquivo.testzip() is not None:
                raise ValueError("Arquivo de limite corrompido")
        ZIP.write_bytes(conteudo)
    with ZipFile(ZIP) as arquivo:
        nomes = {Path(n).suffix.lower(): n for n in arquivo.namelist()}
        encoding = arquivo.read(nomes[".cpg"]).decode("ascii").strip()
        if encoding.isdigit():
            encoding = "cp" + encoding
        leitor = shapefile.Reader(
            shp=io.BytesIO(arquivo.read(nomes[".shp"])),
            shx=io.BytesIO(arquivo.read(nomes[".shx"])),
            dbf=io.BytesIO(arquivo.read(nomes[".dbf"])),
            encoding=encoding,
        )
        crs = CRS.from_wkt(arquivo.read(nomes[".prj"]).decode("utf-8"))
        registros = list(leitor.iterShapeRecords())
        if not registros or any(str(r.record.as_dict()["CD_UF"]) != "35" for r in registros):
            raise ValueError("O limite baixado não corresponde à UF 35")
        geometrias = [transform_geom(crs, "EPSG:4326", r.shape.__geo_interface__) for r in registros]
        features = [
            {"type": "Feature", "properties": r.record.as_dict(), "geometry": g}
            for r, g in zip(registros, geometrias)
        ]
        (LIMITES / "SP_UF_2024.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
            encoding="utf-8",
        )
    return geometrias


def main():
    geometrias = limite_sp()
    somente_validar = "--validar-temporario" in sys.argv
    contagens = Counter()
    temporario = SAIDA.with_suffix(".tmp.tif")
    with rasterio.open(ORIGINAL) as origem:
        if origem.count != 1 or origem.nodata != 0:
            raise ValueError("Raster inesperado: esperado uma banda e NoData 0")
        geometrias = [transform_geom("EPSG:4326", origem.crs, g) for g in geometrias]
        recorte = geometry_window(origem, geometrias)
        transformacao = origem.window_transform(recorte)
        perfil = origem.profile.copy()
        perfil.update(
            width=int(recorte.width), height=int(recorte.height),
            transform=transformacao, compress="deflate", tiled=True,
            blockxsize=256, blockysize=256, BIGTIFF="IF_SAFER",
        )
        print(f"Recortando {perfil['width']} × {perfil['height']} pixels…", flush=True)
        if somente_validar:
            if not temporario.exists():
                raise FileNotFoundError(temporario)
        else:
            gravar_recorte(origem, temporario, perfil, recorte, geometrias, contagens)

    # Valida todos os pixels em janelas maiores para reduzir o custo da máscara.
    verificadas = Counter()
    with rasterio.open(temporario) as destino, rasterio.open(ORIGINAL) as origem:
        assert destino.crs == origem.crs and destino.res == origem.res
        assert destino.dtypes == origem.dtypes and destino.nodata == origem.nodata
        assert destino.transform == transformacao
        assert (destino.width, destino.height) == (perfil["width"], perfil["height"])
        for janela in janelas(destino.width, destino.height):
            dados = destino.read(1, window=janela)
            janela_origem = Window(recorte.col_off + janela.col_off, recorte.row_off + janela.row_off,
                                   janela.width, janela.height)
            esperado = origem.read(1, window=janela_origem)
            fora = geometry_mask(geometrias, out_shape=dados.shape,
                                 transform=destino.window_transform(janela), all_touched=False)
            esperado[fora] = 0
            if not np.array_equal(dados, esperado):
                raise ValueError("O recorte gravado difere dos pixels originais mascarados")
            valores, quantidades = np.unique(dados, return_counts=True)
            if not set(valores.tolist()).issubset({0, 1, 2, 3}):
                raise ValueError("Classes inesperadas no recorte")
            verificadas.update(dict(zip(map(int, valores), map(int, quantidades))))
        assert (not contagens or verificadas == contagens)
        assert sum(verificadas[c] for c in (1, 2, 3)) > 0
        dimensoes = [destino.width, destino.height]
        limites = list(destino.bounds)
    temporario.replace(SAIDA)
    relatorio = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "original": ORIGINAL.name, "recorte": SAIDA.name,
        "fonte_limite": URL, "ano_limite": 2024,
        "crs": str(perfil["crs"]), "dimensoes_colunas_linhas": dimensoes,
        "bounds": limites, "nodata": 0, "all_touched": False,
        "contagem_pixels_por_valor": dict(sorted(verificadas.items())),
        "tamanho_original_bytes": ORIGINAL.stat().st_size,
        "tamanho_recorte_bytes": SAIDA.stat().st_size,
        "validacao": "Todos os pixels conferidos com o original e a máscara estadual.",
        "observacao": "Contagens de pixels não são áreas em hectares.",
    }
    (PASTA / "recorte_sp_metadados.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(relatorio, ensure_ascii=False, indent=2), flush=True)


def janelas(largura, altura):
    for linha in range(0, altura, 2048):
        for coluna in range(0, largura, 2048):
            yield Window(coluna, linha, min(2048, largura - coluna), min(2048, altura - linha))


def gravar_recorte(origem, temporario, perfil, recorte, geometrias, contagens):
    with rasterio.open(temporario, "w", **perfil) as destino:
        destino.update_tags(
            fonte_limite=URL, ano_limite="2024", ano_raster_nome_arquivo="2025",
            regra_borda="centro do pixel (all_touched=False)",
        )
        # Janelas limitam o uso de memória; os pixels não são reamostrados.
        for linha in range(0, perfil["height"], 2048):
            for coluna in range(0, perfil["width"], 2048):
                janela = Window(coluna, linha, min(2048, perfil["width"] - coluna),
                                min(2048, perfil["height"] - linha))
                janela_origem = Window(recorte.col_off + coluna, recorte.row_off + linha,
                                       janela.width, janela.height)
                dados = origem.read(1, window=janela_origem)
                fora = geometry_mask(
                    geometrias, out_shape=dados.shape,
                    transform=destino.window_transform(janela),
                    all_touched=False,
                )
                dados[fora] = 0
                valores, quantidades = np.unique(dados, return_counts=True)
                if not set(valores.tolist()).issubset({0, 1, 2, 3}):
                    raise ValueError("Classes inesperadas no recorte")
                contagens.update(dict(zip(map(int, valores), map(int, quantidades))))
                destino.write(dados, 1, window=janela)
            print(f"  {min(linha + 2048, perfil['height'])}/{perfil['height']} linhas", flush=True)



if __name__ == "__main__":
    main()
