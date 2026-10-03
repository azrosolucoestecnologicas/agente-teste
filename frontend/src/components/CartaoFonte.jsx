import { ChevronDown, FileText } from "lucide-react";
import { useId, useState } from "react";

// Um trecho do material usado na resposta. Clicar mostra o texto do trecho.
export default function CartaoFonte({ fonte }) {
  const [aberto, setAberto] = useState(false);
  const idTrecho = useId();
  const nome = fonte.fonte.replace(/\.(md|pdf)$/i, "");
  const pdf = /\.pdf$/i.test(fonte.fonte);

  return (
    <div
      className={`rounded-xl border bg-white transition dark:bg-slate-900 ${
        aberto ? "border-marca-500 shadow-sm sm:col-span-2" : "border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700"
      }`}
    >
      <button
        type="button"
        onClick={() => setAberto(!aberto)}
        aria-expanded={aberto}
        aria-controls={idTrecho}
        className="flex w-full items-start gap-3 p-3 text-left"
      >
        <span className="grid size-6 shrink-0 place-items-center rounded-md bg-marca-50 text-xs font-semibold text-marca-700 dark:bg-marca-900/60 dark:text-marca-100">
          {fonte.n}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm font-medium text-slate-800 dark:text-slate-100">
            <FileText className="size-3.5 shrink-0 text-slate-400" aria-hidden="true" />
            <span className="truncate">{nome}</span>
            {pdf && (
              <span className="rounded bg-red-50 px-1 text-[10px] font-semibold text-red-700 dark:bg-red-950 dark:text-red-300">PDF</span>
            )}
          </span>
          {fonte.secao && (
            <span className={`mt-0.5 block text-xs text-slate-500 dark:text-slate-400 ${aberto ? "" : "line-clamp-1"}`}>
              {fonte.secao}
            </span>
          )}
        </span>
        <ChevronDown
          className={`mt-0.5 size-4 shrink-0 text-slate-400 transition-transform ${aberto ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>
      {aberto && (
        <div id={idTrecho} className="mx-3 mb-3 max-h-48 overflow-y-auto rounded-lg bg-slate-50 p-3 text-xs leading-relaxed whitespace-pre-wrap text-slate-600 dark:bg-slate-950 dark:text-slate-300">
          {fonte.trecho}
        </div>
      )}
    </div>
  );
}
