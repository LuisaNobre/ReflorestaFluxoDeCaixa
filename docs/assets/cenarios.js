"use strict";

async function iniciarFiltrosCenarios() {
  const status = document.getElementById("scenario-status");
  const cobertura = document.getElementById("scenario-coverage");
  const campos = [
    { id: "faixa", campo: "idFaixaTipo", instrucao: "Selecione uma faixa" },
    { id: "topografia", campo: "idTopografia", instrucao: "Selecione uma topografia" },
    { id: "mecanizacao", campo: "idMecanizacaoNivel", instrucao: "Selecione uma mecanização" },
  ];
  let territorio = window.reflorestaTerritorio;
  let catalogo = null;
  let calculos = null;
  const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  const ha = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  function incluirReserva(r) {
    const reserva = window.reflorestaReservas;
    if (!reserva) return false;
    return reserva.status.some(n => r.ind_status ? n.startsWith(`${r.ind_status} ·`) : n === "Não informado")
      && reserva.condicoes.includes(r.des_condic || "Não informado");
  }
  function mostrarTabela(registros, pares, pronto) {
    const corpo = document.getElementById("scenario-table-body");
    corpo.replaceChildren();
    if (!calculos) return;
    const ids = new Set(registros.map(r => r.linha_excel));
    const fluxos = new Map(calculos.registros.filter(r => ids.has(r.linha_excel)).map(r => [chave(r), r]));
    const todosPares = new Set(catalogo.registros.map(chave));
    const areas = new Map(calculos.areas.map(a => [chave(a), a.area_ha]));
    const areasRL = new Map();
    for (const a of calculos.areas_rl) if (incluirReserva(a)) areasRL.set(chave(a), (areasRL.get(chave(a)) || 0) + a.area_ha);
    for (const [key, par] of [...pares].sort((a,b) => `${a[1].nomeRegiaoEco} ${a[1].descFitofisionomia}`.localeCompare(`${b[1].nomeRegiaoEco} ${b[1].descFitofisionomia}`, "pt-BR"))) {
      const fluxo = pronto ? fluxos.get(key) : null;
      const rl = { vpl: 0, investimento: 0 };
      if (fluxo) for (const r of fluxo.cenario_rl) if (incluirReserva(r)) {
        rl.vpl += r.vpl;
        rl.investimento += r.investimento;
      }
      const situacao = !todosPares.has(key) ? "Sem fluxo de caixa para esta região e fito"
        : !pronto ? "Escolha faixa, topografia e mecanização"
          : !fluxo ? "Sem fluxo de caixa para as condições escolhidas" : "Fluxo disponível";
      const tr = document.createElement("tr");
      tr.dataset.semFluxo = String(!todosPares.has(key) || (pronto && !fluxo));
      const valores = [par.nomeRegiaoEco, par.descFitofisionomia,
        `${ha.format(areas.get(key) || 0)} ha`, fluxo ? moeda.format(fluxo.cenario_total.vpl) : "—",
        fluxo ? moeda.format(fluxo.cenario_total.investimento) : "—",
        `${ha.format(areasRL.get(key) || 0)} ha`, fluxo ? moeda.format(rl.vpl) : "—",
        fluxo ? moeda.format(rl.investimento) : "—", situacao];
      for (const valor of valores) {
        const td = document.createElement("td"); td.textContent = valor; tr.append(td);
      }
      corpo.append(tr);
    }
    document.getElementById("scenario-table-empty").hidden = pares.size > 0;
  }
  function mostrarResultados(registros, pares) {
    const aviso = document.getElementById("scenario-results-status");
    const pronto = campos.every(c => document.getElementById(`scenario-${c.id}`).value);
    mostrarTabela(registros, pares, pronto);
    for (const tipo of ["total", "rl"]) {
      for (const campo of ["area", "vpl", "investimento"]) document.getElementById(`cenario-${tipo}-${campo}`).textContent = "—";
    }
    if (!pronto || !calculos || !window.reflorestaReservas) {
      aviso.textContent = !pronto ? "Escolha uma faixa, uma topografia e uma mecanização para calcular o cenário." : "Carregando resultados pré-calculados…";
      return;
    }
    const ids = new Set(registros.map(r => r.linha_excel));
    const fluxos = calculos.registros.filter(r => ids.has(r.linha_excel));
    const reserva = window.reflorestaReservas;
    const somas = { total: {area_ha:0,vpl:0,investimento:0}, rl: {area_ha:0,vpl:0,investimento:0} };
    for (const fluxo of fluxos) {
      for (const c of Object.keys(somas.total)) somas.total[c] += fluxo.cenario_total[c];
      for (const r of fluxo.cenario_rl) {
        const status = r.ind_status || "";
        const condicao = r.des_condic || "Não informado";
        if (!reserva.status.some(n => status ? n.startsWith(`${status} ·`) : n === "Não informado") || !reserva.condicoes.includes(condicao)) continue;
        for (const c of Object.keys(somas.rl)) somas.rl[c] += r[c];
      }
    }
    for (const tipo of ["total", "rl"]) {
      document.getElementById(`cenario-${tipo}-area`).textContent = `${ha.format(somas[tipo].area_ha)} ha`;
      for (const c of ["vpl", "investimento"]) document.getElementById(`cenario-${tipo}-${c}`).textContent = moeda.format(somas[tipo][c]);
    }
    const cobertos = new Set(fluxos.map(chave));
    const excluida = calculos.areas.filter(a => pares.has(chave(a)) && !cobertos.has(chave(a))).reduce((s,a)=>s+a.area_ha,0);
    aviso.textContent = `${cobertos.size} de ${pares.size} pares região/fito com fluxo. ${ha.format(excluida)} ha de área degradada na seleção sem fluxo, excluídos dos valores. Na base estadual, ${ha.format(calculos.area_baixo_sem_par_ha)} ha sem par territorial também ficam fora dos cenários.`;
  }
  const chave = f => JSON.stringify([f.idRegiaoEco, f.idFitofisionomia]);
  const numero = new Intl.NumberFormat("pt-BR");

  function atualizar() {
    if (!catalogo) return;
    if (!territorio) {
      status.textContent = "Aguardando as regiões e fitofisionomias do mapa.";
      return;
    }
    const pares = new Map(territorio.fitos.map(f => [chave(f), f]));
    const regioes = new Set(territorio.regioes);
    let compativeis = catalogo.registros.filter(r => regioes.has(r.idRegiaoEco) && pares.has(chave(r)));
    let redefinidos = false;
    for (const campo of campos) {
      const select = document.getElementById(`scenario-${campo.id}`);
      const anterior = select.value;
      const permitidos = new Set(compativeis.map(r => r[campo.campo]));
      const opcoes = catalogo.opcoes[campo.id].filter(o => permitidos.has(o.id))
        .sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
      const instrucao = new Option(opcoes.length ? campo.instrucao : "Nenhuma opção disponível", "");
      instrucao.disabled = true;
      select.required = true;
      select.replaceChildren(instrucao);
      opcoes.forEach(o => select.add(new Option(o.nome, o.id)));
      select.disabled = !opcoes.length;
      select.value = permitidos.has(anterior) ? anterior : "";
      if (anterior && !select.value) redefinidos = true;
      if (select.value) compativeis = compativeis.filter(r => r[campo.campo] === select.value);
    }
    const fluxos = new Set(compativeis.map(r => r.idFluxoCaixa));
    mostrarResultados(compativeis, pares);
    const paresComDados = new Set(compativeis.map(chave));
    if (!pares.size) {
      status.textContent = "Selecione pelo menos uma região e uma fitofisionomia no mapa.";
    } else if (!fluxos.size) {
      status.textContent = "Nenhum fluxo de caixa disponível no Excel para esta seleção territorial.";
    } else {
      status.textContent = `${numero.format(fluxos.size)} ${fluxos.size === 1 ? "fluxo de caixa compatível" : "fluxos de caixa compatíveis"} · ${numero.format(paresComDados.size)} de ${numero.format(pares.size)} combinações de região e fitofisionomia com dados.`;
    }
    if (redefinidos) status.textContent += " Opções incompatíveis foram removidas da seleção.";
    const ausentes = [...pares].filter(([key]) => !paresComDados.has(key)).map(([, f]) => f)
      .sort((a, b) => `${a.nomeRegiaoEco} ${a.descFitofisionomia}`.localeCompare(`${b.nomeRegiaoEco} ${b.descFitofisionomia}`, "pt-BR"));
    cobertura.hidden = !ausentes.length;
    const lista = document.getElementById("scenario-missing");
    lista.replaceChildren();
    if (ausentes.length) {
      document.getElementById("scenario-coverage-title").textContent = `${numero.format(ausentes.length)} combinações territoriais sem fluxo para os filtros atuais`;
      for (const item of ausentes) {
        const linha = document.createElement("li");
        linha.textContent = `${item.nomeRegiaoEco} · ${item.descFitofisionomia}`;
        lista.append(linha);
      }
    }
  }

  document.addEventListener("refloresta:territorio", evento => {
    territorio = evento.detail;
    atualizar();
  });
  campos.forEach(campo => document.getElementById(`scenario-${campo.id}`).addEventListener("change", atualizar));
  document.addEventListener("refloresta:reservas", atualizar);
  try {
    const resposta = await fetch("data/filtros_cenarios.json");
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    catalogo = await resposta.json();
    const respostaCalculos = await fetch("data/cenarios.json");
    if (!respostaCalculos.ok) throw new Error("Cenários pré-calculados indisponíveis");
    calculos = await respostaCalculos.json();
    if (calculos.fonte_excel.sha256 !== catalogo.fonte.sha256) throw new Error("Reexporte os cenários após atualizar o Excel");
    if (catalogo.versao_schema !== 1 || !Array.isArray(catalogo.registros)
      || campos.some(campo => !Array.isArray(catalogo.opcoes?.[campo.id]))) {
      throw new Error("Formato dos filtros de cenário incompatível");
    }
    territorio = window.reflorestaTerritorio;
    atualizar();
  } catch (erro) {
    catalogo = null;
    status.textContent = "Não foi possível carregar os filtros de cenário. Gere o catálogo com scripts/preparar_filtros_cenarios.py.";
    campos.forEach(campo => { document.getElementById(`scenario-${campo.id}`).disabled = true; });
    console.error(erro);
  }
}

iniciarFiltrosCenarios();
