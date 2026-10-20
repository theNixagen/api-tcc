const nomes = {
  pendente: "Na fila",
  processando: "Em processamento",
  concluida: "Concluída",
  erro: "Falha no processamento",
  aceita: "Leitura aceita",
  revisao: "Precisa de revisão",
  sem_placa: "Nenhuma placa detectada",
  rejeitada: "Leitura rejeitada",
  aceitar: "Aceitou a leitura",
  rejeitar: "Rejeitou a leitura",
};

export function nomeLeitura(valor) {
  return nomes[valor] || valor || "—";
}
