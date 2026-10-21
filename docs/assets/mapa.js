"use strict";

async function iniciarMapa() {
  const status = document.getElementById("map-status");
  function avisarFalhaAreas() {
    for (const id of ["area-status", "area-rl-status"]) {
      document.getElementById(id).textContent = "Não foi possível ler os dados da seleção. Abra o dashboard pelo servidor HTTP e recarregue a página.";
    }
  }
  if (typeof L === "undefined") {
    status.textContent = "Não foi possível carregar a biblioteca do mapa.";
    avisarFalhaAreas();
    return;
  }
  const mapa = L.map("map", { minZoom: 5, maxZoom: 16, scrollWheelZoom: false });
  mapa.setView([-22.4, -48.6], 7);
  mapa.createPane("vigor").style.zIndex = 350;
  mapa.createPane("regioes").style.zIndex = 410;
  mapa.createPane("fito").style.zIndex = 420;
  L.control.scale({ imperial: false, position: "bottomleft" }).addTo(mapa);
  const base = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    className: "basemap-tiles",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapa);
  const baseInput = document.getElementById("layer-base");
  baseInput.disabled = false;
  baseInput.addEventListener("change", () => baseInput.checked ? base.addTo(mapa) : mapa.removeLayer(base));
  let avisoBase = false;
  base.on("tileerror", () => {
    if (!avisoBase) {
      avisoBase = true;
      document.querySelector(".map-caption").textContent = "Mapa de referência indisponível. As camadas locais continuam disponíveis.";
    }
  });

  const coresRegioes = ["#216055", "#b36825", "#566eb3", "#9a4c72", "#698135", "#7b5d9b"];
  const coresFito = ["#347a62", "#ba8241", "#8174ae", "#679d4f", "#b86c86", "#4f8c9d", "#b6a344", "#846554", "#687fbc", "#b16a49", "#477750", "#9b8aab", "#167f91", "#b44e58", "#757523", "#a24e9c", "#36638c", "#bd8a76", "#7b9740", "#745692", "#477b7c", "#9d6531", "#b08725", "#695e42"];
  const camadas = {};
  const legendas = {};
  const selecoes = {};
  const filtros = {};
  let atualizarTerritorio = () => {};
  let atualizarAreas = () => {};
  let atualizarAreasReservas = () => {};
  const legenda = document.getElementById("map-legend");
  function atualizarLegenda() {
    legenda.replaceChildren();
    for (const id of ["vigor", "regioes", "fito"]) {
      if (!camadas[id] || !mapa.hasLayer(camadas[id])) continue;
      const grupo = document.createElement("div");
      grupo.className = "legend-group";
      grupo.dataset.layer = id;
      const titulo = document.createElement("h3");
      titulo.textContent = legendas[id].titulo;
      grupo.append(titulo);
      for (const [nome, cor] of legendas[id].itens) {
        if (!selecoes[id].has(nome)) continue;
        const item = document.createElement("div");
        item.className = "legend-item";
        const amostra = document.createElement("span");
        amostra.className = `legend-swatch ${id === "regioes" ? "outline" : ""}`;
        amostra.style.setProperty("--swatch", cor);
        const texto = document.createElement("span");
        texto.textContent = nome;
        item.append(amostra, texto);
        grupo.append(item);
      }
      if (selecoes[id].size === 0) {
        const vazio = document.createElement("p");
        vazio.className = "hint";
        vazio.textContent = "Nenhuma classificação selecionada.";
        grupo.append(vazio);
      }
      legenda.append(grupo);
    }
    if (!legenda.children.length) legenda.textContent = "Nenhuma camada temática ativa.";
  }
  function criarFiltro(id, definicao, aplicarFiltro) {
    let nomes = definicao.itens.map(([nome]) => nome);
    const selecionadas = new Set(definicao.selecionadas ?? nomes);
    selecoes[id] = selecionadas;
    const dropdown = document.createElement("details");
    dropdown.className = "class-filter";
    const resumo = document.createElement("summary");
    resumo.setAttribute("aria-label", `Filtrar ${definicao.titulo.toLocaleLowerCase("pt-BR")}`);
    const painel = document.createElement("div");
    painel.className = "filter-panel";
    const acoes = document.createElement("div");
    acoes.className = "filter-actions";
    const lista = document.createElement("div");
    lista.className = "filter-options";
    lista.setAttribute("role", "group");
    lista.setAttribute("aria-label", `Classificações de ${definicao.titulo}`);
    let inputs = [];
    function atualizar() {
      resumo.textContent = nomes.length === 0 ? "Nenhuma opção disponível"
        : selecionadas.size === nomes.length
        ? `Todas as opções (${nomes.length})`
        : selecionadas.size === 0 ? "Nenhuma opção selecionada"
          : `${selecionadas.size} de ${nomes.length} selecionadas`;
      aplicarFiltro(selecionadas);
      atualizarLegenda();
    }
    for (const [texto, marcar] of [["Selecionar todas", true], ["Limpar", false]]) {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.textContent = texto;
      botao.addEventListener("click", () => {
        selecionadas.clear();
        if (marcar) nomes.forEach(nome => selecionadas.add(nome));
        inputs.forEach(input => { input.checked = marcar; });
        atualizar();
      });
      acoes.append(botao);
    }
    function preencher(itens) {
      lista.replaceChildren();
      inputs = [];
      for (const [nome, cor] of itens) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = nome;
      input.checked = selecionadas.has(nome);
      input.addEventListener("change", () => {
        if (input.checked) selecionadas.add(nome);
        else selecionadas.delete(nome);
        atualizar();
      });
      const amostra = document.createElement("span");
      amostra.className = "legend-swatch";
      amostra.style.setProperty("--swatch", cor);
      const texto = document.createElement("span");
      texto.textContent = nome;
      label.append(input, amostra, texto);
      inputs.push(input);
      lista.append(label);
      }
    }
    preencher(definicao.itens);
    painel.append(acoes, lista);
    dropdown.append(resumo, painel);
    document.getElementById(`filter-${id}`).append(dropdown);
    dropdown.addEventListener("toggle", () => {
      if (dropdown.open) {
        document.querySelectorAll(".class-filter[open]").forEach(outro => {
          if (outro !== dropdown) outro.open = false;
        });
        dropdown.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
    document.addEventListener("click", evento => {
      if (!dropdown.contains(evento.target)) dropdown.open = false;
    });
    dropdown.addEventListener("keydown", evento => {
      if (evento.key === "Escape") {
        dropdown.open = false;
        resumo.focus();
      }
    });
    atualizar();
    return {
      definirOpcoes(itens) {
        const todasSelecionadas = nomes.length > 0 && selecionadas.size === nomes.length;
        const semOpcoesAntes = nomes.length === 0;
        nomes = itens.map(([nome]) => nome);
        const anteriores = new Set(selecionadas);
        selecionadas.clear();
        nomes.forEach(nome => {
          if (todasSelecionadas || semOpcoesAntes || anteriores.has(nome)) selecionadas.add(nome);
        });
        preencher(itens);
        // Atualiza o resumo sem disparar novamente a sincronização territorial.
        resumo.textContent = nomes.length === 0 ? "Nenhuma opção disponível"
          : selecionadas.size === nomes.length ? `Todas as opções (${nomes.length})`
            : selecionadas.size === 0 ? "Nenhuma opção selecionada"
              : `${selecionadas.size} de ${nomes.length} selecionadas`;
      },
    };
  }
  function vincular(id, camada, definicao, aplicarOpacidade, aplicarFiltro) {
    camadas[id] = camada;
    legendas[id] = definicao;
    const checkbox = document.getElementById(`layer-${id}`);
    const opacidade = document.getElementById(`opacity-${id}`);
    checkbox.disabled = false;
    filtros[id] = criarFiltro(id, definicao, aplicarFiltro);
    const atualizarOpacidade = () => {
      document.getElementById(`value-${id}`).value = `${opacidade.value}%`;
      aplicarOpacidade(Number(opacidade.value) / 100);
    };
    const atualizarVisibilidade = () => {
      if (checkbox.checked) camada.addTo(mapa);
      else mapa.removeLayer(camada);
      opacidade.disabled = !checkbox.checked;
      atualizarLegenda();
    };
    checkbox.addEventListener("change", atualizarVisibilidade);
    opacidade.addEventListener("input", atualizarOpacidade);
    atualizarOpacidade();
    atualizarVisibilidade();
  }
  function popup(feicao, camada, fitofisionomia = false) {
    const conteudo = document.createElement("div");
    const rotulo = document.createElement("small");
    rotulo.textContent = fitofisionomia ? "REGIÃO E FITOFISIONOMIA" : "REGIÃO ECOLÓGICA";
    const nome = document.createElement("strong");
    nome.textContent = feicao.properties.nomeRegiaoEco || "Região sem nome";
    conteudo.append(rotulo, nome);
    if (fitofisionomia) {
      const detalhe = document.createElement("p");
      detalhe.textContent = feicao.properties.descFitofisionomia || "Sem descrição";
      conteudo.append(detalhe);
    }
    conteudo.className = "feature-popup";
    camada.bindPopup(conteudo);
  }
  async function lerJson(url) {
    const resposta = await fetch(url);
    if (!resposta.ok) throw new Error(`${url}: HTTP ${resposta.status}`);
    return resposta.json();
  }
  try {
    const config = await lerJson("data/mapas/camadas.json");
    if (config.versao_schema !== 1) throw new Error("Versão de camadas incompatível");
    const bounds = L.latLngBounds(config.mapbiomas.bounds);
    mapa.fitBounds(bounds, { padding: [18, 18] });
    mapa.setMaxBounds(bounds.pad(0.5));
    mapa.on("resize", () => mapa.fitBounds(bounds, { padding: [18, 18] }));
    const enquadrar = document.getElementById("enquadrar");
    enquadrar.disabled = false;
    enquadrar.addEventListener("click", () => mapa.fitBounds(bounds, { padding: [18, 18] }));

    // Tiles vazios são transparentes, sem gerar requisições HTTP inexistentes.
    const disponiveis = new Set(config.mapbiomas.tiles);
    const transparente = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=";
    let coresVigorVisiveis = new Set(Object.values(config.mapbiomas.cores).map(cor => parseInt(cor.slice(1), 16)));
    let gruposMascara = [];
    const cacheMascaras = new Map();
    function pathsMascara(zoom) {
      if (cacheMascaras.has(zoom)) return cacheMascaras.get(zoom);
      const mundo = 256 * 2 ** zoom;
      const grupos = gruposMascara.map(feicoes => feicoes.map(feicao => {
        const path = new Path2D();
        const geometria = feicao.geometry;
        const poligonos = geometria.type === "Polygon" ? [geometria.coordinates] : geometria.coordinates;
        for (const poligono of poligonos) for (const anel of poligono) {
          anel.forEach(([lon, lat], indice) => {
            const x = (lon + 180) / 360 * mundo;
            const y = (1 - Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360)) / Math.PI) / 2 * mundo;
            if (indice === 0) path.moveTo(x, y);
            else path.lineTo(x, y);
          });
          path.closePath();
        }
        return path;
      }));
      cacheMascaras.set(zoom, grupos);
      return grupos;
    }
    const CamadaVigor = L.TileLayer.extend({
      getTileUrl(coords) {
        return disponiveis.has(`${coords.z}/${coords.x}/${coords.y}`)
          ? L.TileLayer.prototype.getTileUrl.call(this, coords) : transparente;
      },
      createTile(coords, pronto) {
        const tile = document.createElement("canvas");
        tile.width = tile.height = 256;
        tile.coordenadas = coords;
        const imagem = new Image();
        imagem.onload = () => {
          try {
            const contexto = tile.getContext("2d", { willReadFrequently: true });
            contexto.drawImage(imagem, 0, 0, 256, 256);
            tile.pixelsOriginais = contexto.getImageData(0, 0, 256, 256);
            this.filtrarTile(tile);
            pronto(null, tile);
          } catch (erro) { pronto(erro, tile); }
        };
        imagem.onerror = () => pronto(new Error("Falha ao carregar tile do MapBiomas"), tile);
        imagem.src = this.getTileUrl(coords);
        return tile;
      },
      filtrarTile(tile) {
        if (!tile.pixelsOriginais) return;
        const pixels = new Uint8ClampedArray(tile.pixelsOriginais.data);
        for (let i = 0; i < pixels.length; i += 4) {
          if (!pixels[i + 3]) continue;
          const cor = (pixels[i] << 16) | (pixels[i + 1] << 8) | pixels[i + 2];
          if (!coresVigorVisiveis.has(cor)) pixels[i + 3] = 0;
        }
        tile.getContext("2d").putImageData(new ImageData(pixels, 256, 256), 0, 0);
        // Cada grupo é uma união de polígonos; grupos se intersectam entre si.
        // O preenchimento evenodd mantém os vazios internos de cada feição.
        const coords = tile.coordenadas;
        for (const paths of pathsMascara(coords.z)) {
          const mascara = document.createElement("canvas");
          mascara.width = mascara.height = 256;
          const contextoMascara = mascara.getContext("2d");
          contextoMascara.translate(-coords.x * 256, -coords.y * 256);
          for (const path of paths) contextoMascara.fill(path, "evenodd");
          const contexto = tile.getContext("2d");
          contexto.save();
          contexto.globalCompositeOperation = "destination-in";
          contexto.drawImage(mascara, 0, 0);
          contexto.restore();
        }
      },
      atualizarFiltro() {
        this.getContainer()?.querySelectorAll("canvas").forEach(tile => this.filtrarTile(tile));
      },
    });
    const vigor = new CamadaVigor(`data/mapas/${config.mapbiomas.url}`, {
      pane: "vigor", bounds, noWrap: true,
      minNativeZoom: config.mapbiomas.min_zoom,
      maxNativeZoom: config.mapbiomas.max_native_zoom, maxZoom: 16,
      className: "vigor-tiles", attribution: "MapBiomas · Limite SP: IBGE (2024)",
    });
    let falhaVigor = false;
    vigor.on("tileerror", () => {
      falhaVigor = true;
      status.textContent = "Algumas imagens do MapBiomas não carregaram. Verifique os arquivos publicados.";
    });
    vincular("vigor", vigor, { titulo: "Vigor de pastagens", itens: [
      ["Baixo vigor", config.mapbiomas.cores[1]],
      ["Médio vigor", config.mapbiomas.cores[2]],
      ["Alto vigor", config.mapbiomas.cores[3]],
    ] }, valor => vigor.setOpacity(valor), selecionadas => {
      const nomes = ["Baixo vigor", "Médio vigor", "Alto vigor"];
      coresVigorVisiveis = new Set(nomes.flatMap((nome, i) => selecionadas.has(nome)
        ? [parseInt(config.mapbiomas.cores[i + 1].slice(1), 16)] : []));
      vigor.atualizarFiltro();
      atualizarAreas();
      atualizarAreasReservas();
    });

    const [dadosRegioes, dadosFito] = await Promise.all([
      lerJson(`data/mapas/${config.regioes.arquivo}`),
      lerJson(`data/mapas/${config.fitofisionomias.arquivo}`),
    ]);
    const idsRegioes = new Map(dadosRegioes.features.map(f => [String(f.properties.id), f.properties.nomeRegiaoEco]));
    if (dadosFito.features.some(f => idsRegioes.get(String(f.properties.idRegiaoEco)) !== f.properties.nomeRegiaoEco)) {
      throw new Error("Vínculo de região ecológica inconsistente nas fitofisionomias");
    }
    const dados = dadosRegioes;
    const nomes = [...new Set(dados.features.map(f => f.properties.nomeRegiaoEco))].sort((a, b) => a.localeCompare(b, "pt-BR"));
    const cores = new Map(nomes.map((nome, i) => [nome, coresRegioes[i % coresRegioes.length]]));
    const regioes = L.geoJSON(dados, {
      pane: "regioes", style: f => ({ color: cores.get(f.properties.nomeRegiaoEco), weight: 2.2, fillOpacity: 0.04 }),
      onEachFeature: (f, camada) => popup(f, camada),
    });
    const todasRegioes = regioes.getLayers();
    vincular("regioes", regioes, { titulo: "Regiões ecológicas", itens: [...cores] },
      valor => regioes.setStyle({ opacity: valor, fillOpacity: valor * 0.04 }), () => atualizarTerritorio());
    const nomesFito = [...new Set(dadosFito.features.map(f => f.properties.descFitofisionomia))].sort((a, b) => a.localeCompare(b, "pt-BR"));
    const coresTipos = new Map(nomesFito.map((nome, i) => [nome, coresFito[i % coresFito.length]]));
    const fito = L.geoJSON(dadosFito, {
      pane: "fito", style: f => ({ color: coresTipos.get(f.properties.descFitofisionomia), weight: 1, fillOpacity: 0.55 }),
      onEachFeature: (f, camada) => popup(f, camada, true),
    });
    const todasFito = fito.getLayers();
    vincular("fito", fito, { titulo: "Fitofisionomias", itens: [...coresTipos] },
      valor => fito.setStyle({ opacity: valor, fillOpacity: valor }), () => atualizarTerritorio());

    let ultimaSelecaoRegioes = null;
    atualizarTerritorio = () => {
      mapa.closePopup();
      const idsAtivos = new Set(dadosRegioes.features.filter(f => selecoes.regioes.has(f.properties.nomeRegiaoEco)).map(f => String(f.properties.id)));
      const permitidas = dadosFito.features.filter(f => idsAtivos.has(String(f.properties.idRegiaoEco)));
      const assinatura = [...idsAtivos].sort().join(",");
      if (assinatura !== ultimaSelecaoRegioes) {
        ultimaSelecaoRegioes = assinatura;
        const tipos = new Set(permitidas.map(f => f.properties.descFitofisionomia));
        const itens = [...coresTipos].filter(([nome]) => tipos.has(nome));
        legendas.fito.itens = itens;
        filtros.fito.definirOpcoes(itens);
      }
      const feicoesRegioes = dadosRegioes.features.filter(f => idsAtivos.has(String(f.properties.id)));
      const feicoesFito = permitidas.filter(f => selecoes.fito.has(f.properties.descFitofisionomia));
      // Estado explícito para os filtros de cenário, inclusive quando o catálogo
      // termina de carregar depois da primeira seleção territorial.
      window.reflorestaTerritorio = {
        regioes: feicoesRegioes.map(f => String(f.properties.id)),
        fitos: feicoesFito.map(f => ({
          idRegiaoEco: String(f.properties.idRegiaoEco),
          idFitofisionomia: String(f.properties.idFitoFisionomia),
          nomeRegiaoEco: f.properties.nomeRegiaoEco,
          descFitofisionomia: f.properties.descFitofisionomia,
        })),
      };
      document.dispatchEvent(new CustomEvent("refloresta:territorio", { detail: window.reflorestaTerritorio }));
      const atualizarVetores = (grupo, todas, validas, id, preenchimento) => {
        const ids = new Set(validas.map(f => String(f.properties.id)));
        const opacidade = Number(document.getElementById(`opacity-${id}`).value) / 100;
        todas.forEach(camada => {
          if (ids.has(String(camada.feature.properties.id))) {
            grupo.addLayer(camada);
            camada.setStyle({ opacity: opacidade, fillOpacity: opacidade * preenchimento });
          } else grupo.removeLayer(camada);
        });
      };
      atualizarVetores(regioes, todasRegioes, feicoesRegioes, "regioes", 0.04);
      atualizarVetores(fito, todasFito, feicoesFito, "fito", 1);
      gruposMascara = [];
      if (idsAtivos.size !== dadosRegioes.features.length) gruposMascara.push(feicoesRegioes);
      if (feicoesFito.length !== permitidas.length) gruposMascara.push(feicoesFito);
      cacheMascaras.clear();
      vigor.atualizarFiltro();
      atualizarLegenda();
      atualizarAreas();
      atualizarAreasReservas();
    };
    atualizarTerritorio();
    if (!falhaVigor) status.textContent = "3 camadas disponíveis";
    atualizarLegenda();
    // A geometria e os pixels foram medidos em Python. Aqui só se agregam
    // as áreas da partição pré-calculada que pertencem à seleção atual.
    async function carregarAreas() {
      const areaStatus = document.getElementById("area-status");
      try {
        const areas = await lerJson("data/areas.json");
        if (areas.versao_schema !== 1 || areas.unidade !== "ha" || !areas.registros.length) {
          throw new Error("Formato de áreas incompatível");
        }
        if (areas.regioes.length !== dadosRegioes.features.length || areas.fitos.length !== dadosFito.features.length
          || areas.regioes.some(r => idsRegioes.get(r.id) !== r.nome)
          || areas.fitos.some(f => !dadosFito.features.some(feicao => String(feicao.properties.id) === f.id
            && String(feicao.properties.idRegiaoEco) === f.id_regiao && feicao.properties.descFitofisionomia === f.tipo))) {
          throw new Error("As áreas não correspondem aos identificadores das camadas");
        }
        const registros = areas.registros.map(r => ({ ...r, f: BigInt(r.f) }));
        if (registros.some(r => !Number.isFinite(r.ha) || r.ha < 0)) throw new Error("Área inválida");
        const formatador = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const todosBits = areas.regioes.reduce((bits, r) => bits | (1 << r.bit), 0);
        const nomesClasses = [null, "Baixo vigor", "Médio vigor", "Alto vigor"];
        atualizarAreas = () => {
          const regioesAtivas = areas.regioes.filter(r => selecoes.regioes.has(r.nome));
          const bitsRegioes = regioesAtivas.reduce((bits, r) => bits | (1 << r.bit), 0);
          const ids = new Set(regioesAtivas.map(r => r.id));
          const permitidas = areas.fitos.filter(f => ids.has(f.id_regiao));
          const escolhidas = permitidas.filter(f => selecoes.fito.has(f.tipo));
          const bitsFitos = escolhidas.reduce((bits, f) => bits | (1n << BigInt(f.bit)), 0n);
          const todasRegioes = bitsRegioes === todosBits;
          const todasFitos = escolhidas.length === permitidas.length;
          let areaRegioes = 0, areaFitos = 0;
          const pastagens = [0, 0, 0, 0];
          for (const registro of registros) {
            const emRegiao = (registro.r & bitsRegioes) !== 0;
            const emFito = (registro.f & bitsFitos) !== 0n;
            if (emRegiao) areaRegioes += registro.ha;
            if ((todasRegioes || emRegiao) && emFito) areaFitos += registro.ha;
            if (registro.v > 0 && (todasRegioes || emRegiao) && (todasFitos || emFito)) {
              pastagens[registro.v] += registro.ha;
            }
          }
          document.getElementById("area-regioes").textContent = `${formatador.format(areaRegioes)} ha`;
          document.getElementById("area-fitos").textContent = `${formatador.format(areaFitos)} ha`;
          for (const classe of [1, 2, 3]) {
            const elemento = document.getElementById(`area-vigor-${classe}`);
            const ativa = selecoes.vigor.has(nomesClasses[classe]);
            elemento.dataset.filtered = String(!ativa);
            elemento.textContent = ativa ? `${formatador.format(pastagens[classe])} ha` : "Não selecionado";
          }
        };
        atualizarAreas();
        areaStatus.textContent = "Estimativas em hectares · sem dupla contagem de áreas sobrepostas.";
      } catch (erro) {
        areaStatus.textContent = "Áreas indisponíveis. Execute scripts/calcular_areas.py para gerar os resultados.";
        console.error(erro);
      }
    }
    carregarAreas();
    async function carregarAreasReservas() {
      const aviso = document.getElementById("area-rl-status");
      try {
        const dados = await lerJson("data/areas_reservas_legais.json");
        const campos = ["pastagem_baixo_ha", "pastagem_medio_ha", "pastagem_alto_ha"];
        if (dados.versao_schema !== 2 || dados.unidade !== "ha" || !Array.isArray(dados.registros)
          || dados.registros.some(r => campos.some(c => !Number.isFinite(r[c]) || r[c] < 0))) {
          throw new Error("Agregados de reservas legais incompatíveis");
        }
        const formatador = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const statusLabels = { AT: "Ativo", PE: "Pendente", SU: "Suspenso", CA: "Cancelado" };
        const nomeStatus = valor => valor == null || valor === "" ? "Não informado" : `${valor} · ${statusLabels[valor] || "Código não reconhecido"}`;
        const nomeCondicao = valor => valor == null || valor === "" ? "Não informado" : valor;
        const statusOpcoes = [...new Set(["AT", "PE", "SU", "CA", ...dados.registros.map(r => r.ind_status)])].map(nomeStatus);
        const condicaoOpcoes = [...new Set(dados.registros.map(r => nomeCondicao(r.des_condic)))].sort((a, b) => a.localeCompare(b, "pt-BR"));
        criarFiltro("rl-status", {
          titulo: "Status cadastral", itens: statusOpcoes.map(n => [n, "#607a58"]),
          selecionadas: ["AT", "PE"].map(nomeStatus),
        }, () => atualizarAreasReservas());
        criarFiltro("rl-condicao", {
          titulo: "Condição cadastral", itens: condicaoOpcoes.map(n => [n, "#607a58"]),
          selecionadas: condicaoOpcoes.filter(n => !n.trimStart().toLocaleLowerCase("pt-BR").startsWith("cancelado")),
        }, () => atualizarAreasReservas());
        atualizarAreasReservas = () => {
          window.reflorestaReservas = {
            status: [...selecoes["rl-status"]], condicoes: [...selecoes["rl-condicao"]],
          };
          document.dispatchEvent(new CustomEvent("refloresta:reservas", { detail: window.reflorestaReservas }));
          const ids = new Set(dadosRegioes.features.filter(f => selecoes.regioes.has(f.properties.nomeRegiaoEco)).map(f => String(f.properties.id)));
          const permitidas = dadosFito.features.filter(f => ids.has(String(f.properties.idRegiaoEco)));
          const escolhidas = permitidas.filter(f => selecoes.fito.has(f.properties.descFitofisionomia));
          const fitos = new Set(escolhidas.map(f => String(f.properties.id)));
          const todasRegioes = ids.size === dadosRegioes.features.length;
          const todasFitos = escolhidas.length === permitidas.length;
          const totais = [0, 0, 0];
          for (const r of dados.registros) {
            if (!selecoes["rl-status"].has(nomeStatus(r.ind_status)) || !selecoes["rl-condicao"].has(nomeCondicao(r.des_condic))) continue;
            if (!ids.size || !escolhidas.length) continue;
            if (!todasRegioes && !ids.has(r.regiao_id)) continue;
            if (!todasFitos && !fitos.has(r.fito_id)) continue;
            campos.forEach((campo, i) => { totais[i] += r[campo]; });
          }
          ["Baixo vigor", "Médio vigor", "Alto vigor"].forEach((nome, i) => {
            const elemento = document.getElementById(`area-rl-vigor-${i + 1}`);
            const ativa = selecoes.vigor.has(nome);
            elemento.dataset.filtered = String(!ativa);
            elemento.textContent = ativa ? `${formatador.format(totais[i])} ha` : "Não selecionado";
          });
        };
        atualizarAreasReservas();
        aviso.textContent = "Somas das reservas cadastradas, classificadas por maior área de interseção territorial.";
      } catch (erro) {
        aviso.textContent = "Áreas em reservas legais indisponíveis. Execute scripts/preparar_areas_reservas_legais.py.";
        console.error(erro);
      }
    }
    carregarAreasReservas();
  } catch (erro) {
    status.textContent = "Não foi possível carregar as camadas. Gere os mapas com scripts/preparar_camadas.py e abra por um servidor HTTP.";
    avisarFalhaAreas();
    console.error(erro);
  }
}

iniciarMapa();
