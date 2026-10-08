import { ArrowUp } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

export default function CaixaPergunta({ ref, ocupado, limite, rodape, aoEnviar, aoDigitar, mascote }) {
  const [texto, setTexto] = useState("");
  const interno = useRef(null);

  const ligarRef = (no) => {
    interno.current = no;
    if (typeof ref === "function") ref(no);
    else if (ref) ref.current = no;
  };

  // A caixa cresce com o texto, até umas 8 linhas
  useLayoutEffect(() => {
    const caixa = interno.current;
    if (!caixa) return;
    caixa.style.height = "auto";
    caixa.style.height = `${Math.min(caixa.scrollHeight, 200)}px`;
  }, [texto]);

  // O robô olha para a caixa enquanto há texto sendo escrito
  const temTexto = texto.trim().length > 0;
  useEffect(() => {
    aoDigitar?.(temTexto);
  }, [temTexto, aoDigitar]);

  const passou = texto.length > limite;
  const pode = texto.trim().length > 0 && !passou && !ocupado;

  const enviar = () => {
    if (!pode) return;
    aoEnviar(texto);
    setTexto("");
  };

  return (
    <div className="border-t border-slate-200/70 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
      <form
        className="mx-auto max-w-3xl px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
        onSubmit={(e) => {
          e.preventDefault();
          enviar();
        }}
      >
        <div className="flex items-stretch gap-2">
        {mascote && <div className="lg:hidden">{mascote}</div>}
        <div className="flex flex-1 items-end gap-2 rounded-2xl border border-slate-300 bg-white p-2 shadow-sm transition focus-within:border-marca-500 focus-within:ring-4 focus-within:ring-marca-500/15 dark:border-slate-700 dark:bg-slate-900">
          <label htmlFor="pergunta" className="sr-only">
            Sua pergunta
          </label>
          <textarea
            id="pergunta"
            ref={ligarRef}
            rows={1}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              // Enter envia; Shift+Enter quebra a linha
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                enviar();
              }
            }}
            placeholder={ocupado ? "Aguarde a resposta…" : "Pergunte sobre o material do curso…"}
            className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-1.5 text-base outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={!pode}
            aria-label="Enviar pergunta"
            className="grid size-10 shrink-0 place-items-center rounded-xl bg-marca-600 text-white shadow-sm transition hover:bg-marca-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none dark:disabled:bg-slate-800 dark:disabled:text-slate-600"
          >
            <ArrowUp className="size-5" aria-hidden="true" />
          </button>
        </div>
        </div>
        <div className="mt-2 flex items-center justify-between gap-3 px-1 text-xs text-slate-500 dark:text-slate-400">
          <p>{rodape}</p>
          {texto.length > limite * 0.8 && (
            <p className={passou ? "font-semibold text-red-600 dark:text-red-400" : ""} aria-live="polite">
              {texto.length}/{limite}
            </p>
          )}
        </div>
      </form>
    </div>
  );
}
