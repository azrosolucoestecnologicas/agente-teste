// Conversa com o servidor (FastAPI). Nenhuma chave fica aqui: o front-end só fala com /api.

export class ErroApi extends Error {
  constructor(status, mensagem, retryAfter = null) {
    super(mensagem);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export async function carregarConfig() {
  const r = await fetch("/api/config");
  if (!r.ok) throw new ErroApi(r.status, "Não consegui carregar o assistente.");
  return r.json();
}

/**
 * Envia a pergunta e chama aoEvento(nome, dados) para cada evento do servidor:
 * "fontes", "texto" (vários), e por fim "fim" ou "erro".
 */
export async function perguntar({ mensagem, historico, aoEvento, sinal }) {
  const r = await fetch("/api/perguntar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensagem, historico }),
    signal: sinal,
  });

  if (!r.ok) {
    let detalhe = "";
    try {
      const corpo = await r.json();
      detalhe = typeof corpo.detail === "string" ? corpo.detail : "";
    } catch {
      /* corpo sem JSON */
    }
    const mensagens = {
      413: detalhe || "A pergunta ficou longa demais.",
      422: "Escreva uma pergunta antes de enviar.",
      429: detalhe || "Muitas perguntas seguidas. Espere um pouco.",
    };
    throw new ErroApi(
      r.status,
      mensagens[r.status] || "O servidor não respondeu. Tente de novo em instantes.",
      Number(r.headers.get("Retry-After")) || null,
    );
  }

  // Server-Sent Events: blocos separados por linha em branco, com "event:" e "data:"
  const leitor = r.body.getReader();
  const decodificador = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await leitor.read();
    if (done) break;
    buffer += decodificador.decode(value, { stream: true });
    let fim;
    while ((fim = buffer.indexOf("\n\n")) >= 0) {
      const bloco = buffer.slice(0, fim);
      buffer = buffer.slice(fim + 2);
      let nome = "message";
      let dados = "";
      for (const linha of bloco.split("\n")) {
        if (linha.startsWith("event: ")) nome = linha.slice(7);
        else if (linha.startsWith("data: ")) dados += linha.slice(6);
      }
      if (dados) aoEvento(nome, JSON.parse(dados));
    }
  }
}
