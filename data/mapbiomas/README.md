# Condição de vigor de pastagens

Arquivo inspecionado: `pasture_vigor-brazil_classification_2025.tif`.

## Conferência inicial

- GeoTIFF com uma banda, valores uint8 e CRS EPSG:4326.
- Dimensões: 154470 colunas por 146492 linhas.
- Resolução: aproximadamente 0,000269494585 graus em cada eixo.
- Extensão: longitude -74,020999709 a -32,392171127;
  latitude -34,049023859 a 5,429776922.
- NoData declarado no arquivo: 0. Não contabilizar como pastagem de baixo vigor.
- Cinco janelas de 512 por 512 pixels na região do projeto apresentaram
  valores 0, 1, 2 e 3, compatíveis com a legenda oficial.
- A extensão do raster abrange os limites das seis regiões ecológicas.
  Isso não substitui a verificação de cobertura válida em cada polígono.
- O ano 2025 consta no nome do arquivo, mas não há descrição de banda ou
  metadados internos que comprovem o ano e a coleção da exportação.

## Legenda oficial

1. Baixo vigor.
2. Médio vigor.
3. Alto vigor.

Fonte: https://brasil.mapbiomas.org/iniciativas-e-produtos/cobertura-e-uso-da-terra/pastagem/condicao-de-vigor/

Este produto mede vigor vegetativo de pastagens, não todas as formas de
degradação territorial. A escolha de baixo vigor ou baixo + médio vigor como
base dos cenários deve ser registrada como premissa, antes de calcular áreas.
Não foi adotada nenhuma dessas escolhas nesta conferência.

## Processamento futuro

Recortar por região e CAR, excluir NoData e calcular áreas por classe.
Como as coordenadas estão em graus, não assumir área constante de 900 m² por
pixel: usar cálculo geodésico ou projeção apropriada para áreas. Preservar
classes com reamostragem pelo vizinho mais próximo, caso haja reprojeção.

Esta foi uma inspeção de metadados e amostras, não uma leitura integral de
todos os pixels. Nenhuma área em hectares foi calculada nesta etapa.

## Recorte estadual

Execute `scripts/recortar_mapbiomas_sp.py` com o ambiente de dependências
para gerar `pasture_vigor-sp_classification_2025.tif` a partir do original.
O recorte usa o limite de São Paulo do IBGE (malha territorial de 2024),
guardado em `data/mapas/limites/`. Mantém a grade original sem reamostragem,
com máscara pelo centro do pixel e NoData 0 fora do estado.

`recorte_sp_metadados.json` registra a fonte do limite, os tamanhos, as
contagens por classe e a validação integral do recorte contra o original.
Use o raster estadual nos próximos processamentos referentes a São Paulo.
