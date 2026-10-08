import { AlertTriangle, Check, Clock, Copy, RotateCcw, Sparkles } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CartaoFonte from "./CartaoFonte.jsx";
import Robo from "./Robo.jsx";

function Pensando() {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400" role="status">
      <span className="flex gap-1" aria-hidden="true">
        <span className="ponto size-1.5 rounded-full bg-marca-500" />
        <span className="ponto size-1.5 rounded-full bg-marca-500" />
        <span className="ponto size-1.5 rounded-full bg-marca-500" />
      </span>
      Consultando o material…
    </div>
  );
}

function BotaoCopiar({ texto }) {
  const [copiado, setCopiado] = useState(false);
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    } catch {
      /* sem permissão para a área de transferência */
    }
  };
  return (
    <button
      type="button"
      onClick={copiar}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
    >
      {copiado ? <Check className="size-3.5" aria-hidden="true" /> : <Copy className="size-3.5" aria-hidden="true" />}
      {copiado ? "Copiado" : "Copiar"}
    </button>
  );
}

function AvisoErro({ mensagem, aoTentarDeNovo }) {
  if (mensagem.limite) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
        <Clock className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p>{mensagem.erro}</p>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
      <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
      <p className="flex-1">{mensagem.erro}</p>
      <button
        type="button"
        onClick={aoTentarDeNovo}
        className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 font-medium text-red-700 shadow-sm ring-1 ring-red-200 transition hover:bg-red-100 dark:bg-red-900/40 dark:text-red-100 dark:ring-red-800 dark:hover:bg-red-900/70"
      >
        <RotateCcw className="size-3.5" aria-hidden="true" />
        Tentar de novo
      </button>
    </div>
  );
}

// A expressão do robô no avatar de cada resposta
function avatarDoRobo({ status, naoEncontrado, limite }) {
  if (status === "pensando" || status === "escrevendo") return status;
  if (status === "erro") return limite ? "limite" : "triste";
  return naoEncontrado ? "confuso" : "ocioso";
}

export default function Mensagem({ mensagem, aoTentarDeNovo, mascote }) {
  if (mensagem.role === "user") {
    return (
      <div className="surgir flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-md bg-marca-600 px-4 py-2.5 whitespace-pre-wrap text-white shadow-sm">
          {mensagem.content}
        </p>
      </div>
    );
  }

  const { status, content, fontes = [], naoEncontrado } = mensagem;
  const mostrarFontes = fontes.length > 0 && status === "pronto" && !naoEncontrado;

  return (
    <div className="surgir flex gap-3">
      {mascote ? (
        <div className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-white shadow-sm ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700">
          <Robo corpo={false} estado={avatarDoRobo(mensagem)} className="size-7" />
        </div>
      ) : (
        <div className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-marca-500 to-destaque-600 text-white shadow-sm">
          <Sparkles className="size-4" aria-hidden="true" />
        </div>
      )}
      <div className="min-w-0 flex-1 space-y-3">
        {status === "pensando" && <Pensando />}

        {content && (
          <div
            className={`prose prose-slate max-w-none prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-code:before:content-none prose-code:after:content-none dark:prose-invert ${
              naoEncontrado ? "rounded-xl border border-dashed border-slate-300 p-3 text-slate-600 dark:border-slate-700 dark:text-slate-400" : ""
            }`}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            {status === "escrevendo" && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-marca-500 align-middle" aria-hidden="true" />
            )}
          </div>
        )}

        {status === "erro" && <AvisoErro mensagem={mensagem} aoTentarDeNovo={aoTentarDeNovo} />}

        {mostrarFontes && (
          <section aria-label="Fontes consultadas">
            <h3 className="mb-2 text-xs font-semibold tracking-wider text-slate-500 uppercase dark:text-slate-400">
              Fontes consultadas
            </h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {fontes.map((f) => (
                <CartaoFonte key={f.n} fonte={f} />
              ))}
            </div>
          </section>
        )}

        {status === "pronto" && content && <BotaoCopiar texto={content} />}
      </div>
    </div>
  );
}
