# Camadas publicadas

Geradas por `scripts/preparar_camadas.py`, a partir das fontes de análise.
O HTML lê `camadas.json` para localizar as camadas e montar as legendas.

1. `RegiaoEcologica.geojson`: 6 regiões, com identificadores e nomes.
2. `RegiaoEcoFito.geojson`: 62 feições, com região e descrição de fitofisionomia.
3. `mapbiomas/{z}/{x}/{y}.png`: vigor de pastagens em SP, derivado do raster
   estadual, com cores oficiais (1 baixo, 2 médio, 3 alto) e NoData transparente.

Os vetores têm seleção de campos, reparo de geometrias inválidas (quando
necessário), remoção de componentes não poligonais e simplificação com tolerância
de 0,0002 grau. Apenas a topologia de cada feição é preservada pela simplificação.
Os contadores de geometrias reparadas estão em `camadas.json`.

O raster é reprojetado para EPSG:3857 e reamostrado por vizinho mais próximo
nos zooms 6–12. Tiles totalmente transparentes não são gravados nem solicitados:
a lista de arquivos existentes está no catálogo. Zooms maiores ampliam o nível 12.

Esses arquivos são exclusivamente para visualização. Para cruzamentos e
cálculos, use os dados de análise preservados em `data/`.
O ano 2025 vem do nome do raster recebido, ainda sujeito à confirmação da fonte.

## Filtros territoriais no navegador

O vínculo `RegiaoEcologica.id` → `RegiaoEcoFito.idRegiaoEco` limita as opções e
as feições de fitofisionomia às regiões selecionadas. Os nomes das regiões também
são conferidos. Uma máscara em canvas limita a exibição do vigor às regiões e
às fitofisionomias selecionadas, combinada com o filtro de classes de vigor.
A máscara usa as cópias vetoriais simplificadas e serve somente para exibição.
Nenhum desses filtros altera ou gera novamente os arquivos publicados.
