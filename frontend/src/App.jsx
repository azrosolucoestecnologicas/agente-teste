import { useCallback, useEffect, useRef, useState } from "react";
import { ErroApi, carregarConfig, perguntar } from "./api.js";
import Cabecalho from "./components/Cabecalho.jsx";
import CaixaPergunta from "./components/CaixaPergunta.jsx";
import Conversa from "./components/Conversa.jsx";
import Mascote from "./components/Mascote.jsx";
import Sugestoes from "./components/Sugestoes.jsx";

let proximoId = 0;
const novoId = () => ++proximoId;

// O que o robô está fazendo, a partir da última mensagem da conversa
function estadoDoRobo(mensagens, digitando) {
  const ultima = mensagens[mensagens.length - 1];
  if (ultima?.role === "assistant") {
    if (ultima.status === "pensando") return "pensando";
    if (ultima.status === "escrevendo") return "escrevendo";
    if (ultima.status === "erro") return ultima.limite ? "limite" : "triste";
    if (digitando) return "digitando";
    return ultima.naoEncontrado ? "confuso" : "feliz";
  }
  return digitando ? "digitando" : "ocioso";
}

// Passa as cores do config.yml para as variáveis CSS usadas pelo Tailwind (bg-marca-600 etc.)
function aplicarCores(cores) {
  const raiz = document.documentElement.style;
  for (const [tom, valor] of Object.entries(cores.principal)) raiz.setProperty(`--marca-${tom}`, valor);
  raiz.setProperty("--destaque-500", cores.secundaria["500"]);
  raiz.setProperty("--destaque-600", cores.secundaria["600"]);
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [erroConfig, setErroConfig] = useState(false);
  const [mensagens, setMensagens] = useState([]);
  const [ocupado, setOcupado] = useState(false);
  const [digitando, setDigitando] = useState(false);
  const caixaRef = useRef(null);

  useEffect(() => {
    carregarConfig()
      .then((c) => {
        setConfig(c);
        aplicarCores(c.cores);
        document.title = c.nome;
        // tema_inicial só vale enquanto a pessoa não escolheu um tema no botão
        let salvo = null;
        try {
          salvo = localStorage.getItem("tema");
        } catch {
          /* navegador sem localStorage */
        }
        if (!salvo && c.interface.tema_inicial !== "sistema") {
          document.documentElement.classList.toggle("dark", c.interface.tema_inicial === "escuro");
        }
      })
      .catch(() => setErroConfig(true));
  }, []);

  const atualizar = (id, mudanca) =>
    setMensagens((lista) => lista.map((m) => (m.id === id ? { ...m, ...mudanca(m) } : m)));

  const enviar = useCallback(
    async (texto, base = mensagens) => {
      const pergunta = texto.trim();
      if (!pergunta || ocupado) return;

      // O servidor não guarda nada: a conversa vai inteira a cada pergunta (só as respostas completas)
      const historico = base
        .filter((m) => m.status === "pronto" && m.content)
        .map(({ role, content }) => ({ role, content }));

      const idResposta = novoId();
      setMensagens([
        ...base,
        { id: novoId(), role: "user", content: pergunta, status: "pronto" },
        { id: idResposta, role: "assistant", content: "", fontes: [], status: "pensando", pergunta },
      ]);
      setOcupado(true);

      try {
        await perguntar({
          mensagem: pergunta,
          historico,
          aoEvento: (nome, dados) => {
            if (nome === "fontes") atualizar(idResposta, () => ({ fontes: dados }));
            else if (nome === "texto")
              atualizar(idResposta, (m) => ({ content: m.content + dados.delta, status: "escrevendo" }));
            else if (nome === "fim")
              atualizar(idResposta, () => ({ status: "pronto", naoEncontrado: dados.nao_encontrado }));
            else if (nome === "erro") atualizar(idResposta, () => ({ status: "erro", erro: dados.mensagem }));
          },
        });
        // Se a conexão fechou sem "fim" nem "erro", a resposta ficou pela metade
        atualizar(idResposta, (m) =>
          m.status === "pronto" || m.status === "erro"
            ? {}
            : { status: "erro", erro: "A conexão caiu antes do fim da resposta. Tente de novo." },
        );
      } catch (e) {
        const limite = e instanceof ErroApi && e.status === 429;
        atualizar(idResposta, () => ({
          status: "erro",
          erro: e instanceof ErroApi ? e.message : "Sem conexão com o servidor. Confira sua internet.",
          limite,
          retryAfter: e.retryAfter,
        }));
      } finally {
        setOcupado(false);
        caixaRef.current?.focus();
      }
    },
    [mensagens, ocupado],
  );

  // "Tentar de novo": remove a pergunta e a resposta com erro e envia a pergunta outra vez
  const tentarDeNovo = (idResposta) => {
    const i = mensagens.findIndex((m) => m.id === idResposta);
    if (i < 1) return;
    enviar(mensagens[i].pergunta, mensagens.slice(0, i - 1));
  };

  const novaConversa = () => {
    if (ocupado) return;
    setMensagens([]);
    caixaRef.current?.focus();
  };

  if (erroConfig) {
    return (
      <div className="grid h-full place-items-center p-6 text-center">
        <div>
          <p className="text-lg font-semibold">O assistente não respondeu.</p>
          <p className="mt-1 text-slate-500 dark:text-slate-400">Recarregue a página em alguns instantes.</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="grid h-full place-items-center" role="status" aria-label="Carregando">
        <div className="size-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-500" />
      </div>
    );
  }

  const vazia = mensagens.length === 0;
  const comMascote = config.interface.mascote !== false;
  const ultima = mensagens[mensagens.length - 1];
  const estado = estadoDoRobo(mensagens, digitando);
  const chave = ultima ? `${ultima.id}-${ultima.status}` : "inicio";

  return (
    <div className="flex h-full flex-col">
      <Cabecalho config={config} podeLimpar={!vazia && !ocupado} aoLimpar={novaConversa} />
      <main className="relative flex min-h-0 flex-1 flex-col">
        {vazia ? (
          <Sugestoes
            config={config}
            aoEscolher={(t) => enviar(t)}
            mascote={comMascote && <Mascote variante="inicio" estado={estado} chave={chave} saudacao={`Olá! Eu sou o ${config.nome}. Como posso ajudar?`} />}
          />
        ) : (
          <Conversa mensagens={mensagens} aoTentarDeNovo={tentarDeNovo} mascote={comMascote} />
        )}
        {comMascote && !vazia && <Mascote variante="lateral" estado={estado} chave={chave} />}
      </main>
      <CaixaPergunta
        ref={caixaRef}
        ocupado={ocupado}
        limite={config.interface.limite_caracteres}
        rodape={config.interface.rodape}
        aoEnviar={(t) => enviar(t)}
        aoDigitar={setDigitando}
        mascote={comMascote && !vazia && <Mascote variante="compacto" estado={estado} chave={chave} />}
      />
    </div>
  );
}
