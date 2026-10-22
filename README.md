# Dashboard Refloresta

Análise territorial e financeira de cenários de recuperação de áreas degradadas
no estado de São Paulo.
Python prepara os resultados; o dashboard estático lê somente os arquivos publicados.

Repositório: https://github.com/LuisaNobre/ReflorestaFluxoDeCaixa

O Git versiona os scripts, a documentação e o dashboard pronto em `docs/`,
incluindo seus dados agregados e mapas de visualização. As fontes originais,
o Excel e os resultados analíticos em `data/` permanecem locais, fora do Git;
os READMEs dessas pastas são versionados. Para refazer os cálculos em outra
máquina, disponibilize as fontes nos caminhos documentados abaixo. Para apenas
abrir o dashboard, basta servir a pasta `docs/`, sem executar o processamento.

## Dados originais e dados derivados

**Originais** são arquivos recebidos ou baixados das fontes, preservados sem
alterações pelo projeto. **Derivados** são arquivos produzidos pelo projeto a
partir desses originais, por conversão, recorte, cruzamento ou cálculo.
Ambos podem estar em `data/`; a classificação de cada arquivo está abaixo.

### Dados originais: recebidos ou baixados da fonte

| Arquivo ou conjunto | Origem e referência | Uso |
| --- | --- | --- |
| `data/mapbiomas/pasture_vigor-brazil_classification_2025.tif` | Raster nacional do MapBiomas, adicionado pelo usuário. Produto: condição de vigor de pastagens. O nome indica 2025; ano e coleção ainda precisam ser confirmados com o registro do download. | Entrada para o recorte de São Paulo. Preservado sem alterações. |
| `data/mapas/limites/SP_UF_2024.zip` | Limite estadual de São Paulo, malha territorial do IBGE de 2024, baixado pelo script de recorte. | Contorno para recortar o raster. ZIP preservado no formato recebido. |
| `data/mapas/RegiaoEcologica.geojson` | Arquivo fornecido ao projeto, com 6 regiões. Fonte e versão a documentar. | Base dos mapas e das áreas por região. |
| `data/mapas/RegiaoEcoFito.geojson` | Arquivo fornecido ao projeto, com 62 feições de região e fitofisionomia. Fonte e versão a documentar. | Base das sub-regiões, áreas e filtros territoriais dos cenários. |
| `data/refloresta/MelhorFluxoDeCaixa.xlsx` | Excel fornecido pelo usuário, com atributos territoriais, condições de implantação e indicadores financeiros. Fonte e versão a documentar. | Fonte original dos filtros de cenário. O arquivo é preservado sem alterações; VPLiquido e InvNecessario por hectare alimentam os cenários. |
| `data/car/RESERVA_LEGAL/RESERVA_LEGAL_1.*` e `RESERVA_LEGAL_2.*` | Dois shapefiles fornecidos ao projeto, com 384.421 feições no total. SIRGAS 2000 (EPSG:4674), conforme os `.prj`. Fonte e data de extração a documentar. | Reservas legais para área individual, vigor de pastagens e enquadramento territorial predominante. Arquivos originais preservados. |

Fontes:

- [MapBiomas — condição de vigor de pastagens](https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/pastagem/condicao-de-vigor/).
- [IBGE — limite de São Paulo de 2024, ZIP original](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_UF_2024.zip).

### Dados derivados: transformados ou gerados pelo projeto

| Arquivo gerado | Entradas | Transformação e finalidade |
| --- | --- | --- |
| `data/mapas/limites/SP_UF_2024.geojson` | ZIP original do IBGE. | Conversão do shapefile para GeoJSON em EPSG:4326, respeitando a projeção e a codificação dos originais. Limite sem simplificação. |
| `data/mapbiomas/pasture_vigor-sp_classification_2025.tif` | Raster nacional do MapBiomas + limite estadual do IBGE. | Recorte pelo contorno de São Paulo. Mantém a grade, a resolução e os valores das classes; fora do estado recebe NoData 0. Compressão sem perda. **É o raster que será usado nas próximas análises do projeto.** |
| `data/mapbiomas/recorte_sp_metadados.json` | Execução e validação do recorte. | Registra fonte do limite, parâmetros, dimensões, tamanhos e contagens de pixels. Contagens não equivalem a áreas em hectares. |
| `docs/data/resultados.json` | Atualmente, estrutura inicial definida em `scripts/processar.py`. Futuramente, dados tratados e premissas. | Arquivo lido pelo HTML. Por enquanto contém o estado de espera, listas vazias e indicadores `null`, sem resultados calculados. |
| `docs/data/mapas/RegiaoEcologica.geojson` e `RegiaoEcoFito.geojson` | GeoJSONs correspondentes em `data/mapas/`. | Cópias para visualização: seleção dos campos, reparo de geometrias inválidas, manutenção apenas dos componentes poligonais e simplificação com tolerância de 0,0002 grau. Os originais são preservados. |
| `docs/data/mapas/mapbiomas/{z}/{x}/{y}.png` | GeoTIFF recortado para SP. | Imagens em blocos (tiles) em EPSG:3857, zooms 6–12, reamostradas por vizinho mais próximo. Cores oficiais e NoData transparente. Não usar para calcular áreas. |
| `docs/data/mapas/camadas.json` | Execução de `scripts/preparar_camadas.py`. | Catálogo lido pelo mapa: arquivos, campos, transformações, reparos, cores, extensão e tiles disponíveis. |
| `docs/data/areas.json` | GeoJSONs originais de regiões e fitofisionomias + GeoTIFF recortado para SP. | Áreas pré-calculadas em Python na grade nativa, ponderadas pela área geodésica dos pixels. Registra pertencimentos múltiplos para agregar seleções sem duplicar sobreposições. Inclui método, fontes, hashes e controles. |
| `docs/data/filtros_cenarios.json` | `data/refloresta/MelhorFluxoDeCaixa.xlsx`. | Atributos e identificadores para os filtros de faixa, topografia e mecanização, com vínculo territorial e IDs dos fluxos. Extração por Python, incluindo VPLiquido e InvNecessario por hectare. |
| `data/processados/reservas_legais/<execucao>/` | Shapefiles originais de reservas legais + bases territoriais originais + GeoTIFF de vigor de SP. | SQLite e CSVs individuais, interseções territoriais, agregações por região/fito e por `ind_status`/`des_condic`, resumo e metadados. Área de igual área e pixels de borda fracionários; não usa mapas simplificados. `ultima_execucao.json` identifica a execução concluída. |

O recorte estadual já foi gerado e validado integralmente contra o original e
a máscara estadual, passando de aproximadamente 362 MB para 12,9 MB.
A inclusão na borda segue o centro do pixel (`all_touched=False`). O ano do
limite (2024) é independente do ano indicado no raster (2025).

O MapBiomas utilizado classifica **pastagens por vigor vegetativo**: baixo,
médio e alto. Ainda será definida a seleção de classes que representará a área
considerada degradada nos cenários. O recorte preserva todas as classes.

## Ordem do trabalho

1. **Obter e preservar os originais:** raster nacional MapBiomas, limite IBGE,
   bases territoriais, fluxos de caixa Refloresta e CARs.
2. **Preparar os dados para São Paulo:** raster nacional + limite IBGE →
   raster recortado de SP. Esta etapa já está concluída para o MapBiomas.
3. **Calcular as áreas territoriais:** raster de SP + regiões + fitofisionomias →
   áreas da seleção e das três classes de vigor. Implementado por
   `scripts/calcular_areas.py`. `scripts/calcular_reservas_legais.py` calcula também
   as reservas legais individualmente e agrega seus resultados territoriais e cadastrais.
4. **Calcular os cenários:** áreas + fluxos de caixa + premissas → indicadores
   territoriais e financeiros. Os filtros de condições de implantação e a consulta
   dos fluxos compatíveis já estão implementados; os cálculos permanecem pendentes.
5. **Exportar os resultados para `docs/data/`:** o preparo das três camadas para
   visualização já está implementado e pode ser executado após a etapa 2,
   independentemente dos cálculos. A estrutura inicial do JSON financeiro existe;
   a integração dos cálculos está pendente.
6. **Exibir no HTML e publicar `docs/` no GitHub Pages.**

Os cálculos e cruzamentos são executados em Python antes da publicação.
O HTML lê os resultados exportados. Ao atualizar uma fonte ou premissa,
refaça as etapas que dependem dela, seguindo essa ordem.

## Estrutura

```text
data/
  mapas/          Regiões fornecidas ao projeto
    limites/      ZIP original do IBGE e GeoJSON convertido
  refloresta/     Excel original MelhorFluxoDeCaixa.xlsx
  mapbiomas/      Raster nacional original, recorte de SP e metadados
  car/            Shapefiles originais das reservas legais
  processados/    Resultados individuais e agregados das reservas legais
scripts/          Processamento em Python
docs/
  index.html      Página inicial
  assets/         CSS e JavaScript
  data/           Resultados destinados à publicação
    mapas/        Vetores de visualização, catálogo e tiles do MapBiomas
```

## Executar localmente, na ordem

Execute os comandos na raiz do projeto. As dependências geográficas foram
verificadas com Python 3.14. O gerador inicial de JSON usa apenas a biblioteca
padrão e pode ser executado com Python 3.10 ou superior.

### 1. Preparar o ambiente

Na primeira execução:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### 2. Recortar o MapBiomas para São Paulo

O raster nacional deve estar salvo com o nome indicado no inventário acima.

```powershell
.\.venv\Scripts\python scripts/recortar_mapbiomas_sp.py
```

O script baixa e guarda o limite oficial do IBGE de 2024 em
`data/mapas/limites/`, recorta o raster pelo contorno estadual e gera
`data/mapbiomas/pasture_vigor-sp_classification_2025.tif` e um relatório JSON.
Preserva a resolução, as classes e o arquivo original; pixels fora do estado
recebem NoData 0. A inclusão na borda segue o centro do pixel.

Esta etapa já foi executada. Repita para regenerar o recorte quando necessário.
O ZIP do IBGE já salvo é reutilizado; o raster original permanece preservado.

### 3. Gerar o arquivo consumido pelo HTML

```powershell
.\.venv\Scripts\python scripts/processar.py
```

O script funciona a partir de qualquer diretório e gera `docs/data/resultados.json`.
**Nesta fase, ainda não lê o raster recortado nem calcula áreas ou indicadores.**
Registra apenas a estrutura dos indicadores financeiros ainda não calculados.
As áreas e os filtros do Excel são exportados por scripts separados nas etapas
abaixo. Valores financeiros desconhecidos são `null`.

### 4. Preparar as camadas do mapa

Após gerar o recorte estadual, execute:

```powershell
.\.venv\Scripts\python scripts/preparar_camadas.py
```

Essa etapa já foi executada. O script prepara as duas camadas vetoriais e os
tiles do MapBiomas em `docs/data/mapas/`. Repita quando as respectivas fontes
mudarem. Não depende dos cálculos de cenários ou de `scripts/processar.py`.

As geometrias são reparadas e simplificadas apenas nas cópias de exibição.
A simplificação preserva a topologia de cada feição, sem garantir coincidência
exata entre bordas de feições distintas. O catálogo registra os reparos por
camada. Para análises e áreas, utilize as fontes de análise em `data/`.

### 5. Calcular as áreas da seleção

Após obter o recorte estadual e os GeoJSONs originais, execute:

```powershell
.\.venv\Scripts\python scripts/calcular_areas.py
```

O script lê os dois GeoJSONs de `data/mapas/` e o GeoTIFF estadual, repara
geometrias inválidas sem simplificá-las e gera `docs/data/areas.json`.
Ele não depende dos tiles nem das cópias simplificadas para visualização.
Repita ao atualizar o raster ou qualquer uma das bases territoriais.

As áreas são **estimativas na grade original do MapBiomas**, com inclusão do
pixel pelo centro. Cada pixel recebe uma área em hectares calculada no elipsoide
WGS84, conforme sua latitude; não se assume área fixa de 900 m². A medição dos
territórios também usa essa grade, por isso pode diferir da área vetorial exata.
NoData não entra nas áreas de pastagem, mas não exclui área dos territórios.
O atributo `Area` presente em um dos GeoJSONs não é usado, pois sua unidade
não está documentada; os hectares são calculados pelo método descrito acima.
Os totais das duas bases territoriais não são forçados a coincidir: existem
diferenças de cobertura e sobreposições nos dados originais. Nas seleções
parciais de região, a área das fitofisionomias considera também o recorte pelas
regiões selecionadas, assim como a máscara territorial do vigor.

Cada pixel registra a combinação de regiões, fitofisionomias e classe de vigor
a que pertence. Essas combinações formam parcelas disjuntas: o HTML soma apenas
as áreas pré-calculadas compatíveis com a seleção, sem duplicar sobreposições.
Não há medição geográfica ou leitura de GeoTIFF no navegador.

O painel mostra áreas das regiões selecionadas, das fitofisionomias selecionadas
e dos três níveis de vigor no território filtrado. Os totais consideram toda
a seleção, independentemente do zoom, da opacidade e da visibilidade das camadas.
Uma classe de vigor desmarcada aparece como “Não selecionado”, em vez de ser
confundida com ausência de pastagem. Seleções territoriais vazias têm área zero.
Com todas as regiões e fitofisionomias selecionadas, as pastagens representam
todo o raster de SP, incluindo pixels eventualmente fora dos polígonos regionais,
como já ocorre na visualização.

### 6. Preparar os filtros de cenário do Excel

Após adicionar ou atualizar `data/refloresta/MelhorFluxoDeCaixa.xlsx`, execute:

```powershell
.\.venv\Scripts\python scripts/preparar_filtros_cenarios.py
```

O script identifica a aba pelos cabeçalhos, lê os atributos e gera
`docs/data/filtros_cenarios.json`, com a fonte, a aba, o hash SHA-256 e a linha
original de cada registro. Preserva os nomes das opções, remove apenas espaços
nas extremidades e padroniza os IDs como texto. Exporta também VPLiquido e InvNecessario por hectare para a preparação dos cenários.

O navegador cruza os pares selecionados de região e fitofisionomia com os IDs
do Excel. `RegiaoEcoFito.idRegiaoEco` corresponde a `idRegiaoEco` e
`RegiaoEcoFito.idFitoFisionomia` corresponde a `idFitofisionomia` no Excel.
Não é feita correspondência aproximada por nome.

Os seletores de cenário usam `nomeFaixa`, `nomeTopografia` e `nomeMecanizacao`,
começam em “Todas” e seguem a ordem faixa → topografia → mecanização.
As opções dependem do território e das condições anteriores. Valores que deixam
de ser compatíveis são removidos da seleção. O painel mostra a quantidade de
fluxos distintos e a cobertura das combinações territoriais escolhidas.
Os filtros de cenário não modificam os mapas nem os indicadores de área.

Há combinações territoriais do mapa sem correspondência no Excel atual: o
painel lista essas faltas para os filtros em uso, sem atribuir um fluxo de outra
região ou fitofisionomia. Os atributos de região administrativa são preservados
no catálogo para uso futuro, mas não há seletor adicional nesta etapa.

Atualizar somente esse Excel exige executar apenas esse script e atualizar
o JSON publicado; não é necessário refazer os mapas ou as áreas.

### 7. Calcular as reservas legais e suas agregações

```powershell
.\.venv\Scripts\python scripts/calcular_reservas_legais.py
```

O script lê os dois shapefiles em `data/car/RESERVA_LEGAL/`, os dois GeoJSONs
originais de `data/mapas/` e o GeoTIFF estadual. Não depende das imagens do mapa
nem dos totais em `docs/data/areas.json`. Calcula por feição:

- Área total em hectares, em projeção elipsoidal de igual área para São Paulo.
- Área das pastagens de baixo, médio e alto vigor, incluindo frações dos pixels
  nas bordas, em vez de contar somente seus centros.
- Região e fito predominantes pela maior área de interseção, separadamente,
  com áreas e percentuais de todas as interseções salvos para auditoria.
- Atributos de origem, incluindo `cod_imovel`, `ind_status` e `des_condic`.

Os resultados ficam em `data/processados/reservas_legais/<execucao>/`.
O arquivo `ultima_execucao.json`, na pasta superior, aponta para a execução
completa. Há SQLite, CSV individual, CSV de interseções, dez níveis de agregação
e resumo JSON. Entre eles estão os totais por região/fito, por `ind_status`,
por `des_condic` e pelo cruzamento dos dois atributos.

Cada registro contribui com sua área inteira no par predominante; a área não
é dividida proporcionalmente entre os territórios. A classificação independente
pode produzir região e fito com hierarquia divergente; esses casos são sinalizados
sem alterar a regra de maior interseção. Registros sem correspondência continuam
nos totais, com classificação nula.

As somas são de feições cadastradas, sem dissolver sobreposições entre reservas
ou deduplicar imóveis. Elas não são a área da união física das reservas.
O método e os campos estão descritos no
[README das reservas legais](data/processados/reservas_legais/README.md).

O processamento salva lotes em transações SQLite. Se for interrompido, rode
novamente o mesmo comando para continuar. Se mudar uma fonte ou o código, uma
nova pasta é criada automaticamente pelas assinaturas dos arquivos, preservando
as execuções anteriores. É possível limitar os processos com `--workers 4`.

Os resultados individuais ficam em `data/`. Para atualizar os três indicadores
de pastagem em reservas legais na área de seleção, depois do cálculo execute:

```powershell
.\.venv\Scripts\python scripts/preparar_areas_reservas_legais.py
```

Esse comando lê a última execução completa e confere os totais antes de gerar
`docs/data/areas_reservas_legais.json`, contendo somente agregados por região/fito,
sem identificadores de imóveis. Não refaz as interseções geográficas.
Ao atualizar as fontes, rode primeiro `calcular_reservas_legais.py` e depois
esse exportador. O HTML apenas filtra e soma esses resultados.

Os indicadores acompanham região, fito e vigor, além dos filtros locais de
`ind_status` (AT · Ativo, PE · Pendente, SU · Suspenso, CA · Cancelado) e
`des_condic` (categorias originais da fonte). Ambos permitem múltipla seleção,
iniciam com AT e PE selecionados no status e com as condições que começam com
“Cancelado” desmarcadas (sem distinguir maiúsculas/minúsculas). As demais
condições começam selecionadas. Afetam somente as pastagens em reservas legais.
As duas condições são combinadas; limpar qualquer filtro resulta em zero.
O exportador usa os agregados já calculados por região/fito/status/condição.
Com todas as fitos disponíveis
marcadas, usa-se o total da região predominante; com seleção parcial, exige-se
também a fito predominante selecionada. Isso preserva os casos de hierarquia
divergente nos totais regionais. Sem seleção territorial, as áreas são zero.
Com todo o estado selecionado, incluem-se os cadastros sem classificação.
Zoom, opacidade e visibilidade das camadas não alteram os valores.

### 8. Abrir o dashboard localmente

Na raiz do projeto:

```powershell
.\.venv\Scripts\python -m http.server 8000 --directory docs
```

Abra http://localhost:8000. Use o servidor local para permitir a leitura do JSON.

O mapa permite ligar/desligar as três camadas, ajustar a opacidade, consultar
nomes por clique, ampliar e voltar ao enquadramento estadual. As regiões
ecológicas e o MapBiomas iniciam ativos; as fitofisionomias podem ser ativadas
no painel. As legendas acompanham as camadas ativas.

Abaixo da opacidade, cada camada tem um filtro com seleção múltipla:
regiões ecológicas, tipos de fitofisionomia ou classes de vigor (baixo, médio
e alto). Todas as opções começam marcadas. É possível selecionar todas,
limpar a seleção ou marcar opções individuais. As legendas mostram apenas
as opções selecionadas; a seleção é preservada ao desligar e religar a camada
durante a sessão, mas volta ao padrão quando a página é recarregada.
Os filtros territoriais são encadeados: `RegiaoEcologica.id` corresponde a
`RegiaoEcoFito.idRegiaoEco`, com conferência de `nomeRegiaoEco`. O filtro de
fitofisionomias lista apenas os tipos presentes nas regiões selecionadas, e
apenas as feições dessas regiões podem aparecer. As cores dos tipos são mantidas
ao trocar a região. Se todas as opções estavam marcadas, a nova lista começa
inteiramente marcada; em seleções parciais, são mantidos os tipos ainda disponíveis.
Ao retornar de uma lista sem opções, as novas opções começam marcadas.

O vigor é limitado às regiões escolhidas e, quando houver seleção parcial de
fitofisionomias, à interseção dessas sub-regiões com as regiões escolhidas.
Limpar as regiões ou as fitofisionomias deixa o vigor sem pixels visíveis.
Desligar os contornos de uma camada não remove seus filtros territoriais.
Selecionar novamente todas as regiões e fitofisionomias restaura a cobertura de SP.

Nos vetores, o navegador mostra apenas as feições das classificações selecionadas.
No MapBiomas, os tiles existentes são desenhados em canvas, tornando transparentes
os pixels das classes desmarcadas pelas suas cores oficiais. Uma máscara
geográfica adicional, construída com os polígonos de visualização selecionados,
oculta o vigor fora do território escolhido, respeitando os vazios internos.
As máscaras são reprojetadas para a grade de exibição e reutilizadas por nível
de zoom. As bordas têm a precisão das geometrias simplificadas e do desenho
do navegador; não são um recorte analítico do GeoTIFF. Os pixels de exibição
originais ficam em memória para restaurar as classes ao selecioná-las novamente.
Isso altera somente a visualização, sem modificar os PNGs, os GeoTIFFs ou os
resultados de análise, e não exige gerar as camadas novamente.

Leaflet 1.9.4 e sua licença estão salvos em `docs/assets/vendor/leaflet/`.
As camadas temáticas são arquivos estáticos locais; o mapa de referência
OpenStreetMap precisa de internet e pode ser desligado no painel. Sua camada
recebe um filtro visual de tons de cinza, com contraste reduzido, aplicado apenas
ao fundo. As cores temáticas do MapBiomas e dos vetores são preservadas.
Os tiles locais têm detalhe nativo até o zoom 12; ampliações posteriores
apenas ampliam as imagens existentes. A visualização não substitui o GeoTIFF
de análise nem serve para medições.

### 9. Publicar no GitHub Pages

Depois de criar o repositório e enviar os arquivos, configure o GitHub Pages
para publicar a pasta `/docs` da branch escolhida. Não há publicação automática
configurada nesta etapa. Ao atualizar os dados, execute o processamento e envie
também os resultados gerados.

A pasta `docs/` deve conter somente o conteúdo destinado ao dashboard público.
Os arquivos de origem e de processamento ficam em `data/`. Os mapas preparados
para visualização já são exportados para `docs/data/mapas/`.

## Próximas etapas

### Cálculos dos cenários

Depois de atualizar áreas, agregados das reservas e Excel, execute nesta ordem:

```powershell
.\.venv\Scripts\python scripts/preparar_filtros_cenarios.py
.\.venv\Scripts\python scripts/preparar_areas_reservas_legais.py
.\.venv\Scripts\python scripts/preparar_cenarios.py
```

O último comando gera `docs/data/cenarios.json`: para cada fluxo, multiplica
os valores conforme descrito abaixo. Fluxos com `InvNecessario < 0` são
excluídos na exportação do catálogo, antes de gerar opções, contagens e cenários.
São tratados como indisponíveis; suas áreas continuam na tabela, sem valores
financeiros quando não há fluxo válido. O Excel original permanece inalterado.
A quantidade excluída fica em `excluidos_investimento_negativo` no catálogo.
Investimento zero e VPL negativo são mantidos.

Para cada fluxo válido, o script multiplica
os hectares de baixo vigor do seu par `idRegiaoEco`/`idFitofisionomia` por
`VPLiquido` e `InvNecessario`, em R$/ha. As multiplicações são realizadas em
Python. O navegador soma resultados somente após escolher as três condições.
Nas reservas, os produtos são separados também por status e condição cadastral.
Os filtros cadastrais afetam apenas esse cenário. O filtro visual de vigor não
altera a definição de área degradada: sempre baixo vigor.

As áreas gerais usam os átomos já calculados na grade original, exigindo
pertencimento à região e à fito com essa região como pai. Em sobreposições,
atribui-se o átomo à fito elegível de menor ID original para evitar duplicação.
Áreas sem par territorial e pares sem fluxo não recebem valores financeiros;
a interface informa a cobertura. Nas reservas, preserva-se o par predominante
independente e a soma cadastral. Só entram pares presentes na seleção territorial
com fluxo correspondente. Não se aplica o fluxo de outro par nem se somam
alternativas de implantação. Duplicidade de fluxos para a mesma combinação
interrompe a exportação. VPL negativo é mantido, sem truncamento.

- Conferir identificadores de regiões, unidades, datas e sistemas de coordenadas.
- Completar os registros de fonte, coleção, versão e ano dos dados recebidos.
- Definir as classes de vigor consideradas nos cenários de degradação.
- Definir a eventual análise por união física das reservas, além das somas cadastrais já calculadas.
- Ampliar as premissas dos cenários e os indicadores financeiros.
- Ampliar a consulta das reservas legais por status e condição cadastral.
- Permitir percentuais de recuperação e novos indicadores além de VPL e investimento.
