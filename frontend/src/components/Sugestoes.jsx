import { ArrowUpRight, Sparkles } from "lucide-react";

// Tela inicial: apresentação e as perguntas de exemplo do config.yml
export default function Sugestoes({ config, aoEscolher }) {
  return (
    <div className="relative flex-1 overflow-y-auto">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-80 bg-[radial-gradient(ellipse_at_top,var(--marca-100),transparent_70%)] opacity-80 dark:bg-[radial-gradient(ellipse_at_top,var(--marca-900),transparent_70%)] dark:opacity-50"
      />
      <div className="relative mx-auto flex min-h-full max-w-3xl flex-col justify-center px-4 py-10">
        <div className="surgir text-center">
          {config.logo_url ? (
            <img
              src={config.logo_url}
              alt=""
              style={{ height: config.logo_altura * 1.4 }}
              className="mx-auto w-auto rounded-2xl shadow-lg ring-1 ring-black/5"
            />
          ) : (
            <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-marca-500 to-destaque-600 text-white shadow-lg">
              <Sparkles className="size-8" aria-hidden="true" />
            </div>
          )}
          <h2 className="mt-6 text-3xl font-bold tracking-tight sm:text-4xl">
            <span className="bg-gradient-to-r from-marca-600 to-destaque-600 bg-clip-text text-transparent dark:from-marca-500 dark:to-destaque-500">
              {config.nome}
            </span>
          </h2>
          {config.descricao && (
            <p className="mx-auto mt-3 max-w-xl text-base text-slate-600 sm:text-lg dark:text-slate-400">
              {config.descricao}
            </p>
          )}
        </div>

        {config.exemplos.length > 0 && (
          <div className="mt-10">
            <p className="mb-3 text-center text-xs font-semibold tracking-wider text-slate-500 uppercase dark:text-slate-400">
              Comece por uma destas
            </p>
            <ul className="grid gap-3 sm:grid-cols-2">
              {config.exemplos.map((exemplo, i) => (
                <li key={exemplo} className="surgir" style={{ animationDelay: `${i * 60}ms` }}>
                  <button
                    type="button"
                    onClick={() => aoEscolher(exemplo)}
                    className="group flex h-full w-full items-start justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-left text-sm font-medium text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-marca-500 hover:shadow-md focus-visible:outline-2 focus-visible:outline-marca-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-marca-500"
                  >
                    <span>{exemplo}</span>
                    <ArrowUpRight
                      className="size-4 shrink-0 text-slate-400 transition group-hover:text-marca-600 dark:group-hover:text-marca-500"
                      aria-hidden="true"
                    />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
