# Limite estadual de São Paulo

Fonte: IBGE, Malha Territorial 2024, unidade da federação 35.

https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_UF_2024.zip

O script `scripts/recortar_mapbiomas_sp.py` mantém o ZIP original e converte
suas geometrias para GeoJSON em EPSG:4326, respeitando a projeção declarada
no arquivo `.prj` do shapefile. O limite não é simplificado antes do recorte.
O ano da malha (2024) é independente do ano indicado no raster (2025).
