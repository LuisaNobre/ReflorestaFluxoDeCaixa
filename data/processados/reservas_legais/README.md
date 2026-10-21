# Reservas legais: resultados de processamento

Gerados por `scripts/calcular_reservas_legais.py`, a partir dos dois shapefiles
de `data/car/RESERVA_LEGAL/`, das bases territoriais originais e do GeoTIFF de
vigor de pastagens recortado para São Paulo.

## Localizar a execução concluída

`ultima_execucao.json` aponta para a pasta da última execução completa e traz os
totais e controles. Cada execução tem uma subpasta identificada pelas assinaturas
das fontes e do código. Pastas sem conclusão são pontos de retomada ou execuções
anteriores; não representam o resultado consolidado atual.

O comando padrão continua os lotes já salvos da mesma versão. Alterar qualquer
fonte ou o código cria outra pasta, preservando os resultados anteriores.

```powershell
.\.venv\Scripts\python scripts/calcular_reservas_legais.py
```

O parâmetro opcional `--workers 4` reduz o número de processos numéricos. O padrão
usa até 12 processos, deixando quatro CPUs lógicas disponíveis quando possível.
`--limite 1000` processa até mil registros novos e salva o ponto de retomada.

## Arquivos de cada execução

- `reservas.sqlite`: base principal, com tabelas `reservas`, `intersecoes`,
  `progresso` e dez tabelas `agregado_*`.
- `reservas_individuais.csv`: um registro por feição do shapefile original.
- `intersecoes_territoriais.csv`: todas as interseções positivas com regiões e
  fitofisionomias, com área e percentual da reserva.
- `agregado_regiao_fito.csv`: totais por região e fito predominantes.
- `agregado_regiao_fito_status.csv`: mesma agregação por `ind_status`.
- `agregado_regiao_fito_condicao.csv`: mesma agregação por `des_condic`.
- `agregado_regiao_fito_status_condicao.csv`: cruzamento dos dois atributos.
- `agregado_regiao.csv` e `agregado_fito.csv`: totais de cada dimensão.
- `agregado_total.csv`, `agregado_status.csv`, `agregado_condicao.csv` e
  `agregado_status_condicao.csv`: totais gerais e por atributos, sem dimensão territorial.
- `resumo.json`: as agregações, fontes, método e controles de qualidade.
- `metadados.json`: método, fontes, hashes SHA-256 e versões das bibliotecas.
- `progresso.json`: andamento auxiliar; o ponto de retomada efetivo fica no SQLite.

Os CSVs têm codificação UTF-8 com BOM, separador `;` e ponto decimal. Na importação
em planilhas, informe esses parâmetros. O SQLite preserva a precisão numérica
e distingue valores nulos de textos vazios.

## Unidade de análise e identificação

Cada feição original é tratada como uma reserva; multipartes permanecem no mesmo
registro e os vazios internos são respeitados. `rl_id` combina o nome do arquivo
com o FID do GDAL (começando em zero), rastreável por `arquivo_origem` e `fid_origem`.
Esse identificador é válido para a versão da fonte; não é um código oficial de
reserva nem necessariamente permanece igual após substituir/reordenar a fonte.

São preservados `cod_imovel`, `cod_tema`, `nom_tema`, `ind_status` e `des_condic`.
`num_area_origem` conserva o atributo `num_area` sem usá-lo como área calculada.
Um imóvel pode ter várias feições; não são deduplicadas por `cod_imovel`.

## Método de área e pastagens

As geometrias são lidas como SIRGAS 2000 (EPSG:4674), conforme os arquivos `.prj`.
As áreas são medidas em uma projeção elipsoidal de igual área (LAEA), centrada em
São Paulo; sua definição completa está nos metadados. As bases originais não são
simplificadas. Geometrias inválidas são reparadas antes e, se necessário, após
a reprojeção, com o indicador `geometria_reparada`.
O GDAL também pode corrigir a orientação dos anéis durante a leitura; o
indicador contabiliza os reparos explícitos adicionais feitos pelo Shapely.

`area_total_ha` é a área inteira da feição reparada. Para cada classe do raster,
o processamento mede a interseção da reserva com os polígonos dos pixels na
mesma projeção de igual área. Pixels de borda entram proporcionalmente à sua
interseção, inclusive para reservas menores que um pixel.

`pastagem_baixo_ha`, `pastagem_medio_ha` e `pastagem_alto_ha` correspondem às
classes 1, 2 e 3. O código 0 não é contado como pastagem. `area_sem_vigor_ha`
é o restante da área, incluindo áreas sem informação de vigor e fora da
cobertura do raster; não é uma classificação de uso do solo.

Esse método fracionário é diferente da estimativa pelos centros dos pixels usada
em `docs/data/areas.json`; é mais adequado aos limites de reservas pequenas.

## Classificação territorial

A região predominante e a fito predominante são escolhidas **separadamente**
pela maior área de interseção. Não se usa centroide, proximidade ou número de pixels.
Se houver empate em até 1e-9 ha, escolhe-se o menor ID textual e registra-se o empate.

- `regiao_id`/`regiao_nome`: região predominante.
- `regiao_intersecao_ha` e `regiao_percentual`: sua interseção com a reserva.
- `fito_id`: ID da feição de `RegiaoEcoFito` (não o ID geral do tipo de vegetação).
- `fitofisionomia_id`/`fito_nome`: identificação do tipo de fitofisionomia.
- `fito_regiao_id`: região à qual a fito pertence nos atributos da base.
- `fito_intersecao_ha` e `fito_percentual`: interseção da fito predominante.
- `hierarquia_consistente`: 1 se a região predominante coincide com a região
  da fito predominante, 0 se divergem, nulo se alguma classificação não existe.

A escolha independente pode produzir uma divergência de hierarquia quando a
reserva atravessa territórios. Esses casos não são forçados a outra categoria;
as interseções completas permitem revisar a regra futuramente.
Sem interseção positiva, a classificação fica nula e o registro continua nos totais.

## Agregação e controles

Toda a área de cada reserva e suas três áreas de pastagem são atribuídas ao
par predominante, mesmo quando a reserva atravessa outros territórios. A área
não é repartida proporcionalmente entre regiões nesta agregação.

Os totais são somas das feições cadastradas. Reservas sobrepostas ou repetidas
na fonte contribuem separadamente; esses valores não são a área da união física
de todas as reservas. Cada registro contribui uma vez em cada nível de agregação.

As agregações mantêm também grupos nulos, contam registros e áreas válidas e
verificam a conservação dos totais de todas as áreas. `situacao='erro'` e `erro`
identificam registros sem resultado válido, com áreas nulas, sem inventar zeros.
O resumo contabiliza erros, falta de classificação, reparos e divergências.

Os arquivos individuais permanecem em `data/`, fora do conteúdo publicado em
`docs/`. Nenhum resultado é publicado automaticamente no dashboard nesta etapa.
