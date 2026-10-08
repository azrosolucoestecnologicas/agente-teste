import { SquarePen } from "lucide-react";
import AlternarTema from "./AlternarTema.jsx";

export default function Cabecalho({ config, podeLimpar, aoLimpar }) {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex max-w-4xl items-center gap-3 px-4 py-3">
        {config.logo_url && (
          <img
            src={config.logo_url}
            alt=""
            style={{ height: Math.min(config.logo_altura, 44) }}
            className="w-auto shrink-0 rounded-lg shadow-sm ring-1 ring-black/5"
          />
        )}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">{config.nome}</h1>
          {config.descricao && (
            <p className="hidden truncate text-sm text-slate-500 sm:block dark:text-slate-400">{config.descricao}</p>
          )}
        </div>
        <button
          type="button"
          onClick={aoLimpar}
          disabled={!podeLimpar}
          className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:pointer-events-none disabled:opacity-0 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <SquarePen className="size-4" aria-hidden="true" />
          <span className="hidden sm:inline">Nova conversa</span>
          <span className="sr-only sm:hidden">Nova conversa</span>
        </button>
        <AlternarTema />
      </div>
    </header>
  );
}
