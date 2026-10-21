"use strict";

const numero = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function exibir(id, valor, formato, sufixo = "") {
  document.getElementById(id).textContent = Number.isFinite(valor)
    ? formato.format(valor) + sufixo
    : "—";
}

async function carregar() {
  try {
    const resposta = await fetch("data/resultados.json");
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    const dados = await resposta.json();
    if (dados.versao_schema !== 1 || !dados.indicadores) {
      throw new Error("Formato de resultados incompatível");
    }
    document.getElementById("status").textContent = dados.mensagem;
    exibir("area-degradada", dados.indicadores.area_degradada_ha, numero, " ha");
    exibir("area-recuperada", dados.indicadores.area_recuperada_ha, numero, " ha");
    exibir("investimento", dados.indicadores.investimento_brl, moeda);
    document.getElementById("atualizacao").textContent =
      `Arquivo gerado em ${new Date(dados.atualizado_em).toLocaleString("pt-BR", { timeZone: "America/Bahia" })}.`;
  } catch (erro) {
    document.getElementById("status").textContent =
      "Não foi possível carregar os resultados. Gere o arquivo com Python e abra a página por um servidor HTTP.";
    console.error(erro);
  }
}

carregar();
