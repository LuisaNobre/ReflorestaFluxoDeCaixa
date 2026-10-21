"""Áreas, vigor e enquadramento predominante de cada registro de reserva legal.

Execução incremental, com resultados individuais e interseções em SQLite,
exportações CSV e agregações. Não modifica nem dissolve os registros de origem.
"""

import argparse
import csv
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor
import sqlite3
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyogrio
from pyogrio.raw import read
from pyproj import CRS, Transformer
import rasterio
import shapely
from shapely import STRtree

RAIZ = Path(__file__).resolve().parents[1]
LAEA = "+proj=laea +lat_0=-23 +lon_0=-48 +datum=WGS84 +units=m +no_defs"
COLUNAS = ["rl_id", "arquivo_origem", "fid_origem", "cod_imovel", "cod_tema", "nom_tema",
           "num_area_origem", "ind_status", "des_condic", "area_total_ha",
           "pastagem_baixo_ha", "pastagem_medio_ha", "pastagem_alto_ha", "area_sem_vigor_ha",
           "regiao_id", "regiao_nome", "regiao_intersecao_ha", "regiao_percentual",
           "fito_id", "fitofisionomia_id", "fito_nome", "fito_regiao_id", "fito_intersecao_ha",
           "fito_percentual", "hierarquia_consistente", "geometria_reparada",
           "empate_regiao", "empate_fito", "situacao", "erro"]
AREAS = ["area_total_ha", "pastagem_baixo_ha", "pastagem_medio_ha", "pastagem_alto_ha", "area_sem_vigor_ha"]
ATRIBUTOS = ["cod_imovel", "cod_tema", "nom_tema", "num_area", "ind_status", "des_condic"]


def agora():
    return datetime.now(timezone.utc).isoformat()


def salvar_json(caminho, dados):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=caminho.parent,
                                     prefix=".rl-", suffix=".tmp", delete=False) as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        tmp = Path(arquivo.name)
    # O diretório é sincronizado pelo Dropbox, que pode bloquear renomeações
    # brevemente. O checkpoint científico está na transação SQLite.
    for tentativa in range(50):
        try:
            tmp.replace(caminho)
            return
        except PermissionError:
            if tentativa == 49:
                if caminho.name == "progresso.json":
                    print("JSON de progresso ocupado; checkpoint SQLite preservado.", flush=True)
                    return
                raise
            time.sleep(.2)


def assinatura(caminho):
    with caminho.open("rb") as arquivo:
        digest = hashlib.file_digest(arquivo, "sha256").hexdigest()
    return {"arquivo": caminho.relative_to(RAIZ).as_posix(), "bytes": caminho.stat().st_size, "sha256": digest}


def poligonal(g):
    if g is None or g.is_empty:
        return None, False
    reparada = not g.is_valid
    if reparada:
        g = shapely.make_valid(g)
    def partes(h):
        if h.geom_type == "Polygon":
            yield h
        elif hasattr(h, "geoms"):
            for parte in h.geoms:
                yield from partes(parte)
    polys = list(partes(g))
    if not polys:
        return None, reparada
    g = polys[0] if len(polys) == 1 else shapely.MultiPolygon(polys)
    if not g.is_valid:
        g = shapely.union_all(polys)
        reparada = True
    return g, reparada


class Territorios:
    def __init__(self, caminho):
        dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
        t = Transformer.from_crs(4326, LAEA, always_xy=True)
        self.props, geometrias = [], []
        for feicao in dados["features"]:
            g, _ = poligonal(shapely.geometry.shape(feicao["geometry"]))
            if g is None:
                raise ValueError(f"Território sem polígono: {caminho}")
            projetada, _ = poligonal(shapely.transform(g, t.transform, interleaved=False))
            if projetada is None:
                raise ValueError(f"Território degenerado após reprojeção: {caminho}")
            geometrias.append(projetada)
            self.props.append(feicao["properties"])
        self.geometrias = np.array(geometrias, dtype=object)
        shapely.prepare(self.geometrias)
        self.arvore = STRtree(self.geometrias)

    def classificar(self, reserva, area_total):
        intersecoes = []
        for i in self.arvore.query(reserva):
            territorio = self.geometrias[i]
            if not shapely.intersects(territorio, reserva):
                continue
            area = area_total if shapely.covers(territorio, reserva) else shapely.intersection(territorio, reserva).area / 10000
            if area > 1e-10:
                intersecoes.append((int(i), float(area)))
        intersecoes.sort(key=lambda x: (-x[1], str(self.props[x[0]]["id"])))
        if not intersecoes:
            return None, 0., False, []
        i, maior = intersecoes[0]
        empate = len(intersecoes) > 1 and math.isclose(maior, intersecoes[1][1], rel_tol=0, abs_tol=1e-9)
        if empate:
            empatadas = [x for x in intersecoes if math.isclose(x[1], maior, rel_tol=0, abs_tol=1e-9)]
            i, maior = min(empatadas, key=lambda x: str(self.props[x[0]]["id"]))
        return self.props[i], maior, empate, [(str(self.props[j]["id"]), a) for j, a in intersecoes]


class Pastagens:
    def __init__(self, caminho, cache=None):
        with rasterio.open(caminho) as origem:
            if origem.crs.to_epsg() != 4326 or origem.nodata != 0 or origem.count != 1:
                raise ValueError("Esperado raster EPSG:4326 com uma banda e NoData 0")
            self.dados = np.load(cache, mmap_mode="r") if cache else origem.read(1)
            self.t = origem.transform
        self.h, self.w = self.dados.shape
        self.projetar = Transformer.from_crs(4326, LAEA, always_xy=True)

    def medir(self, reserva_geo, reserva_metros):
        xmin, ymin, xmax, ymax = reserva_geo.bounds
        t = self.t
        c0, c1 = max(0, math.floor((xmin-t.c)/t.a)), min(self.w, math.ceil((xmax-t.c)/t.a))
        r0, r1 = max(0, math.floor((ymax-t.f)/t.e)), min(self.h, math.ceil((ymin-t.f)/t.e))
        totais = np.zeros(4, dtype=float)
        shapely.prepare(reserva_metros)
        # A fração dos pixels de borda é medida por interseção, inclusive para
        # reservas menores que um pixel. Não se usa uma máscara só pelos centros.
        for inicio in range(r0, r1, 256):
            imagem = self.dados[inicio:min(r1, inicio+256), c0:c1]
            linhas, colunas = np.nonzero(imagem)
            for pos in range(0, len(linhas), 16384):
                rr, cc = linhas[pos:pos+16384], colunas[pos:pos+16384]
                classes = imagem[rr, cc]
                if not np.isin(classes, [1, 2, 3]).all():
                    raise ValueError("Classe inesperada de pastagem")
                esquerda = t.c+(cc+c0)*t.a
                topo = t.f+(rr+inicio)*t.e
                pixels = shapely.box(esquerda, topo+t.e, esquerda+t.a, topo)
                pixels = shapely.transform(pixels, self.projetar.transform, interleaved=False)
                dentro = shapely.intersects(reserva_metros, pixels)
                if not dentro.any():
                    continue
                pixels, classes = pixels[dentro], classes[dentro]
                completos = shapely.covers(reserva_metros, pixels)
                areas = shapely.area(pixels)
                if not completos.all():
                    areas[~completos] = shapely.area(shapely.intersection(reserva_metros, pixels[~completos]))
                totais += np.bincount(classes, weights=areas/10000, minlength=4)
        return totais[1:]


def abrir_banco(caminho):
    banco = sqlite3.connect(caminho)
    banco.execute("PRAGMA journal_mode=WAL")
    numericas = set(AREAS + ["num_area_origem", "regiao_intersecao_ha", "regiao_percentual", "fito_intersecao_ha", "fito_percentual"])
    inteiras = {"fid_origem", "hierarquia_consistente", "geometria_reparada", "empate_regiao", "empate_fito"}
    defs = [f'{c} {"REAL" if c in numericas else "INTEGER" if c in inteiras else "TEXT"}' + (" PRIMARY KEY" if c == "rl_id" else "") for c in COLUNAS]
    banco.execute("CREATE TABLE IF NOT EXISTS reservas ("+",".join(defs)+")")
    banco.execute("CREATE TABLE IF NOT EXISTS intersecoes (rl_id TEXT, tipo TEXT, territorio_id TEXT, area_ha REAL, percentual_rl REAL, PRIMARY KEY(rl_id,tipo,territorio_id))")
    banco.execute("CREATE TABLE IF NOT EXISTS progresso (arquivo TEXT PRIMARY KEY, processados INTEGER)")
    banco.execute("CREATE INDEX IF NOT EXISTS idx_reservas_situacao ON reservas(situacao)")
    banco.commit()
    return banco


def exportar(banco, pasta, meta):
    dims = ["regiao_id", "regiao_nome", "fito_id", "fitofisionomia_id", "fito_nome", "fito_regiao_id"]
    somas = ["COUNT(*) AS n_reservas", "COUNT(area_total_ha) AS n_areas_validas",
             "SUM(CASE WHEN situacao='erro' THEN 1 ELSE 0 END) AS n_erros"] + [f"SUM({c}) AS {c}" for c in AREAS]
    def csv_sql(nome, sql):
        cur = banco.execute(sql)
        with (pasta / nome).open("w", newline="", encoding="utf-8-sig") as arquivo:
            writer = csv.writer(arquivo, delimiter=";")
            writer.writerow([c[0] for c in cur.description])
            writer.writerows(cur)
    csv_sql("reservas_individuais.csv", "SELECT * FROM reservas ORDER BY arquivo_origem,fid_origem")
    csv_sql("intersecoes_territoriais.csv", "SELECT * FROM intersecoes ORDER BY rl_id,tipo,area_ha DESC")
    grupos = {
        "regiao_fito": dims,
        "regiao_fito_status": dims + ["ind_status"],
        "regiao_fito_condicao": dims + ["des_condic"],
        "regiao_fito_status_condicao": dims + ["ind_status", "des_condic"],
        "regiao": dims[:2], "fito": dims[2:],
        "total": [], "status": ["ind_status"], "condicao": ["des_condic"],
        "status_condicao": ["ind_status", "des_condic"],
    }
    resumo = {}
    for nome, colunas in grupos.items():
        tabela = "agregado_" + nome
        banco.execute(f"DROP TABLE IF EXISTS {tabela}")
        sql = "SELECT " + ",".join(colunas+somas) + " FROM reservas"
        if colunas:
            sql += " GROUP BY " + ",".join(colunas)
        banco.execute(f"CREATE TABLE {tabela} AS " + sql)
        csv_sql(tabela+".csv", f"SELECT * FROM {tabela}")
        cur = banco.execute(f"SELECT * FROM {tabela}")
        resumo[nome] = [dict(zip([c[0] for c in cur.description], row)) for row in cur]
    total = resumo["total"][0]
    for nome in grupos:
        for coluna in AREAS:
            agregado = sum((r[coluna] or 0) for r in resumo[nome])
            if not math.isclose(agregado, total[coluna] or 0, rel_tol=1e-10, abs_tol=1e-6):
                raise ValueError(f"Agregação não conserva totais: {nome}/{coluna}")
        if sum(r["n_reservas"] for r in resumo[nome]) != total["n_reservas"]:
            raise ValueError(f"Agregação perde registros: {nome}")
    banco.commit()
    controles = {"sem_regiao": banco.execute("SELECT COUNT(*) FROM reservas WHERE regiao_id IS NULL").fetchone()[0],
                 "sem_fito": banco.execute("SELECT COUNT(*) FROM reservas WHERE fito_id IS NULL").fetchone()[0],
                 "hierarquia_divergente": banco.execute("SELECT COUNT(*) FROM reservas WHERE hierarquia_consistente=0").fetchone()[0],
                 "geometrias_reparadas": banco.execute("SELECT COUNT(*) FROM reservas WHERE geometria_reparada=1").fetchone()[0]}
    salvar_json(pasta / "resumo.json", {"metadados": meta, "concluido_em": agora(), "controles": controles, "agregacoes": resumo})
    banco.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return total, controles


_CONTEXTO = {}


def iniciar_worker(rpath, fpath, vpath, cache):
    _CONTEXTO.update(regioes=Territorios(Path(rpath)), fitos=Territorios(Path(fpath)),
                     pastagens=Pastagens(Path(vpath), cache), transformacoes={})


def calcular_registro(item):
    arquivo, fid, wkb, attrs, crs = item
    transformacoes = _CONTEXTO["transformacoes"]
    if crs not in transformacoes:
        transformacoes[crs] = (Transformer.from_crs(crs, 4326, always_xy=True),
                               Transformer.from_crs(crs, LAEA, always_xy=True))
    proj_geo, proj_metros = transformacoes[crs]
    territorios_r, territorios_f, pastagens = _CONTEXTO["regioes"], _CONTEXTO["fitos"], _CONTEXTO["pastagens"]
    rl_id = f"{Path(arquivo).stem}:{int(fid)}"
    registro = dict.fromkeys(COLUNAS)
    registro.update(rl_id=rl_id, arquivo_origem=arquivo, fid_origem=int(fid),
                    cod_imovel=attrs["cod_imovel"], cod_tema=attrs["cod_tema"], nom_tema=attrs["nom_tema"],
                    num_area_origem=attrs["num_area"], ind_status=attrs["ind_status"], des_condic=attrs["des_condic"])
    intersecoes = []
    try:
        g, reparada = poligonal(shapely.from_wkb(wkb))
        registro["geometria_reparada"] = int(reparada)
        if g is None:
            raise ValueError("Geometria sem componente poligonal")
        geo = shapely.transform(g, proj_geo.transform, interleaved=False)
        metros, reparada_projecao = poligonal(shapely.transform(g, proj_metros.transform, interleaved=False))
        registro["geometria_reparada"] = int(reparada or reparada_projecao)
        if metros is None:
            raise ValueError("Geometria sem área após reprojeção")
        area = metros.area/10000
        if area <= 0 or not math.isfinite(area):
            raise ValueError("Área nula ou inválida")
        r, ar, er, ir = territorios_r.classificar(metros, area)
        f, af, ef, iff = territorios_f.classificar(metros, area)
        vigor = pastagens.medir(geo, metros)
        if vigor.sum() > area+max(1e-6, area*1e-7):
            raise ValueError(f"Pastagem excede a área da reserva: {vigor.sum()} > {area}")
        registro.update(area_total_ha=area, pastagem_baixo_ha=float(vigor[0]),
                        pastagem_medio_ha=float(vigor[1]), pastagem_alto_ha=float(vigor[2]),
                        area_sem_vigor_ha=max(0., area-float(vigor.sum())),
                        regiao_id=str(r["id"]) if r else None, regiao_nome=r["nomeRegiaoEco"] if r else None,
                        regiao_intersecao_ha=ar, regiao_percentual=100*ar/area,
                        fito_id=str(f["id"]) if f else None, fitofisionomia_id=str(f["idFitoFisionomia"]) if f else None,
                        fito_nome=f["descFitofisionomia"] if f else None,
                        fito_regiao_id=str(f["idRegiaoEco"]) if f else None, fito_intersecao_ha=af, fito_percentual=100*af/area,
                        hierarquia_consistente=int(str(r["id"]) == str(f["idRegiaoEco"])) if r and f else None,
                        empate_regiao=int(er), empate_fito=int(ef), situacao="ok")
        intersecoes += [(rl_id, tipo, territorio, a, 100*a/area) for tipo, itens in [("regiao", ir), ("fito", iff)] for territorio, a in itens]
    except Exception as erro:
        registro.update(situacao="erro", erro=f"{type(erro).__name__}: {erro}")
    return tuple(registro[c] for c in COLUNAS), intersecoes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=RAIZ/"data"/"processados"/"reservas_legais")
    parser.add_argument("--limite", type=int, help="Processa no máximo N registros novos, mantendo o ponto de retomada")
    parser.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2)-4)), help="Processos num?ricos paralelos")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers deve ser positivo")
    arquivos = sorted((RAIZ/"data"/"car"/"RESERVA_LEGAL").glob("*.shp"))
    if not arquivos:
        raise FileNotFoundError("Nenhum shapefile de reserva legal encontrado")
    rpath = RAIZ/"data"/"mapas"/"RegiaoEcologica.geojson"
    fpath = RAIZ/"data"/"mapas"/"RegiaoEcoFito.geojson"
    vpath = RAIZ/"data"/"mapbiomas"/"pasture_vigor-sp_classification_2025.tif"
    print("Conferindo fontes e assinaturas SHA-256…", flush=True)
    fontes = [assinatura(p) for shp in arquivos for p in [shp, shp.with_suffix('.shx'), shp.with_suffix('.dbf'), shp.with_suffix('.prj')]]
    fontes += [assinatura(p) for p in (rpath, fpath, vpath)]
    meta = {"schema": 1, "fontes": fontes, "codigo_sha256": assinatura(Path(__file__).resolve())["sha256"],
            "projecao_area": LAEA, "encoding_dbf": "CP1252 (sem .cpg; verificado nos atributos)",
            "metodo": "Área em LAEA elipsoidal de São Paulo; geometrias originais reparadas sem simplificação. Interseção fracionária com os pixels categóricos do raster. Região e fito dominantes escolhidos independentemente por maior interseção; empate em 1e-9 ha resolvido pelo menor ID textual. A área inteira da reserva é agregada ao par dominante, sem repartição territorial.",
            "agregacao": "Soma por registro de origem, sem dissolver sobreposições entre reservas ou deduplicar cadastros. Os totais são áreas cadastradas somadas, não a união territorial das reservas.",
            "unidade": "ha", "versoes": {"shapely": shapely.__version__, "pyogrio": pyogrio.__version__, "rasterio": rasterio.__version__}}
    chave = hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:16]
    pasta = args.saida.resolve()/chave
    pasta.mkdir(parents=True, exist_ok=True)
    salvar_json(pasta/"metadados.json", meta)
    banco = abrir_banco(pasta/"reservas.sqlite")
    infos = {p.name: pyogrio.read_info(p) for p in arquivos}
    esperado = sum(info["features"] for info in infos.values())
    concluidos = banco.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    print(f"Execução {chave}: {concluidos}/{esperado} registros já salvos; {pasta}", flush=True)
    if concluidos < esperado:
        cache = RAIZ/".venv"/"cache_reservas"/(fontes[-1]["sha256"]+".npy")
        cache.parent.mkdir(parents=True, exist_ok=True)
        if not cache.exists():
            print("Preparando raster compartilhado de leitura?", flush=True)
            with rasterio.open(vpath) as origem, cache.with_suffix(".tmp.npy").open("wb") as destino:
                np.save(destino, origem.read(1))
            cache.with_suffix(".tmp.npy").replace(cache)
        pool = ProcessPoolExecutor(max_workers=args.workers, initializer=iniciar_worker,
                                   initargs=(str(rpath), str(fpath), str(vpath), str(cache)))
        novos, inicio = 0, time.monotonic()
        for arquivo in arquivos:
            info = infos[arquivo.name]
            quantidade = info["features"]
            check = banco.execute("SELECT processados FROM progresso WHERE arquivo=?", (arquivo.name,)).fetchone()
            offset = check[0] if check else 0
            while offset < quantidade:
                tamanho = min(4096, quantidade-offset)
                if args.limite is not None:
                    tamanho = min(tamanho, args.limite-novos)
                if tamanho <= 0:
                    break
                dados, fids, wkbs, atributos = read(arquivo, skip_features=offset, max_features=tamanho,
                                                   return_fids=True, encoding="CP1252", columns=ATRIBUTOS)
                if not len(fids):
                    raise ValueError(f"Leitura terminou antes da contagem declarada: {arquivo}/{offset}")
                linhas, intersecoes = [], []
                itens = [(arquivo.name, int(fid), wkbs[n],
                          {campo: coluna[n] for campo, coluna in zip(dados["fields"], atributos)}, info["crs"])
                         for n, fid in enumerate(fids)]
                for registro, cruzamentos in pool.map(calcular_registro, itens, chunksize=16):
                    linhas.append(registro)
                    intersecoes.extend(cruzamentos)
                with banco:
                    banco.executemany("INSERT INTO reservas VALUES ("+",".join("?" for _ in COLUNAS)+")", linhas)
                    banco.executemany("INSERT INTO intersecoes VALUES (?,?,?,?,?)", intersecoes)
                    offset += len(fids)
                    banco.execute("INSERT OR REPLACE INTO progresso VALUES (?,?)", (arquivo.name, offset))
                novos += len(fids)
                total = banco.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
                erros = banco.execute("SELECT COUNT(*) FROM reservas WHERE situacao='erro'").fetchone()[0]
                salvar_json(pasta/"progresso.json", {"atualizado_em": agora(), "salvos": total, "esperados": esperado, "erros": erros, "completo": False})
                print(f"{total}/{esperado} · {erros} erros · {novos/max(time.monotonic()-inicio, .001):.1f} registros/s", flush=True)
            if args.limite is not None and novos >= args.limite:
                break
        pool.shutdown()
    total_salvo = banco.execute("SELECT COUNT(*) FROM reservas").fetchone()[0]
    if total_salvo == esperado:
        print("Exportando resultados individuais, interseções e agregações…", flush=True)
        total, controles = exportar(banco, pasta, meta)
        salvar_json(pasta/"progresso.json", {"atualizado_em": agora(), "salvos": total_salvo, "esperados": esperado, "completo": True, "controles": controles})
        salvar_json(args.saida.resolve()/"ultima_execucao.json", {"execucao": chave, "pasta": str(pasta), "concluido_em": agora(), "total": total, "controles": controles})
        print(json.dumps({"pasta": str(pasta), "total": total, "controles": controles}, ensure_ascii=False, indent=2), flush=True)
    else:
        print("Processamento parcial salvo. Execute novamente o mesmo comando para continuar.", flush=True)
    banco.close()


if __name__ == "__main__":
    main()
