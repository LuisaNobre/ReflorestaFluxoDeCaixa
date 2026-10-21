# Resultados publicados

`resultados.json` é gerado por `python scripts/processar.py`; evite editá-lo manualmente.
O HTML lê esse arquivo sem executar cálculos financeiros ou geográficos.

- `versao_schema`: versão do formato consumido pelo JavaScript.
- `atualizado_em`: data de geração em UTC.
- `premissas`: parâmetros adotados no processamento.
- `indicadores`: resultados gerais; `null` significa resultado ainda indisponível.
- `regioes`, `cenarios`, `mapas`, `fontes`: listas inicialmente vazias, cujos
  registros serão definidos junto com a integração dos dados.

Adicione aqui somente arquivos destinados à publicação. Mapas preparados para
o navegador estão em `mapas/`, com documentação em `mapas/README.md`.

## Áreas da seleção

`areas.json` é gerado por `scripts/calcular_areas.py`, sem usar as cópias de
visualização. Contém estimativas em hectares sobre a grade do GeoTIFF de SP,
com inclusão pelo centro do pixel e área geodésica WGS84 por linha.

- `fontes`: arquivos originais, hashes SHA-256 e contagem de reparos geométricos.
- `grade`: projeção, resolução, dimensões, extensão e área mínima/máxima do pixel.
- `regioes` e `fitos`: identificadores originais, hierarquia e posição de cada
  feição na codificação de pertencimento.
- `registros`: parcelas disjuntas com `r` (pertencimento às regiões), `f`
  (pertencimento às fitofisionomias, inteiro serializado como texto), `v`
  (classe de vigor: 0 sem dados de vigor, 1 baixo, 2 médio, 3 alto), `ha`
  (área pré-calculada) e `pixels` (quantidade de pixels).
- `controle_vigor_sp_ha` e `controle_pixels_vigor`: totais estaduais para
  conferir a conservação das áreas e dos pixels das três classes.

Cada bit indica pertencimento a uma feição. Um pixel pode pertencer a várias
feições sobrepostas, mas está em apenas um registro; qualquer seleção conta sua
área uma única vez. A interface agrega os registros segundo os mesmos filtros
territoriais usados na máscara do mapa. Os contornos de exibição são
simplificados; os números usam a grade e as geometrias originais reparadas.
Essas estimativas não são medições cadastrais de imóveis nem áreas oficiais
de unidades territoriais.

## Filtros de cenários

`filtros_cenarios.json` é gerado por `scripts/preparar_filtros_cenarios.py`,
a partir do Excel original `data/refloresta/MelhorFluxoDeCaixa.xlsx`.

- `fonte`: arquivo, aba e hash SHA-256 do Excel.
- `opcoes`: IDs e nomes de faixa, topografia e mecanização.
- `registros`: atributos territoriais, condições de implantação,
  `idCombinacao`, `idFluxoCaixa` e `linha_excel` para rastreabilidade.

Os IDs são textos; os nomes são os da fonte, com espaços nas extremidades
removidos. `VPLiquido` e `InvNecessario` são exportados em reais por hectare.

`cenarios.json` é gerado por `scripts/preparar_cenarios.py`, após os filtros,
áreas e agregados das reservas. Contém os produtos de área de baixo vigor por
VPL e investimento unitários, por fluxo e por status/condição nas reservas.
O navegador apenas seleciona e soma esses produtos. A origem do Excel é
conferida por SHA-256. Pares sem fluxo não são estimados por outros territórios.
`areas_rl` mantém as áreas por par/status/condição independentemente da
disponibilidade de fluxo, permitindo mostrar na tabela áreas sem VPL ou
investimento calculável. A tabela acompanha os filtros territoriais e cadastrais;
valores financeiros só aparecem após selecionar as três condições de implantação.
O HTML filtra os registros por pares de região/fitofisionomia e pelas condições
de implantação. O catálogo é independente de `resultados.json` e de `areas.json`.
# Pastagens em reservas legais

`areas_reservas_legais.json` é derivado da última execução completa de
`scripts/calcular_reservas_legais.py`, exportado por
`scripts/preparar_areas_reservas_legais.py`. O schema 2 usa hectares e contém
`execucao`, `calculado_em`, `controles`, `total` e `registros` por
`regiao_id`/`fito_id` predominantes (IDs originais, strings ou null),
`ind_status` e `des_condic` originais. Esses dois últimos campos permitem
filtrar as somas por status e condição, combinando ambos os critérios.
Cada registro traz a quantidade de reservas e as áreas de pastagem de baixo,
médio e alto vigor. Não contém dados individuais dos imóveis.
São somas cadastrais, preservando sobreposições entre reservas. A classificação
territorial atribui toda a área da reserva ao território de maior interseção.
Os filtros do navegador apenas somam esses agregados, sem cálculos geográficos.

