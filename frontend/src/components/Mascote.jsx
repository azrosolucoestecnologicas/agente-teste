import { useEffect, useRef, useState } from "react";
import Robo from "./Robo.jsx";

// O que o robô diz em cada momento da conversa
const FALAS = {
  digitando: "Estou ouvindo…",
  pensando: "Procurando no material…",
  escrevendo: "Escrevendo a resposta…",
  feliz: "Pronto! Confira as fontes da resposta.",
  confuso: "Hum… não achei isso no material.",
  triste: "Ops! Algo deu errado. Tente de novo.",
  limite: "Calma! Muitas perguntas seguidas.",
};

// Reações que duram alguns segundos e depois voltam ao normal
const PASSAGEIRAS = new Set(["feliz", "confuso", "triste", "limite"]);

// Para onde o robô olha enquanto a pessoa digita (a caixa de pergunta)
const OLHAR_DIGITANDO = { lateral: { x: -3, y: 3 }, compacto: { x: 3.5, y: 0.5 }, inicio: { x: 0, y: 3.5 } };

/** Os olhos seguem o ponteiro do mouse (ou o dedo) pela tela. */
function useOlhar(ref) {
  const [olhar, setOlhar] = useState({ x: 0, y: 0 });
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let quadro = 0;
    const mover = (e) => {
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(() => {
        const caixa = ref.current?.getBoundingClientRect();
        if (!caixa || !caixa.width) return;
        const dx = e.clientX - (caixa.left + caixa.width / 2);
        const dy = e.clientY - (caixa.top + caixa.height * 0.35);
        const d = Math.hypot(dx, dy) || 1;
        const forca = Math.min(1, d / 250);
        setOlhar({ x: (dx / d) * 4 * forca, y: (dy / d) * 3 * forca });
      });
    };
    window.addEventListener("pointermove", mover, { passive: true });
    return () => {
      window.removeEventListener("pointermove", mover);
      cancelAnimationFrame(quadro);
    };
  }, [ref]);
  return olhar;
}

/** O estado que aparece: as reações passageiras duram 4 segundos. */
function useEstadoExibido(estado, chave) {
  const [exibido, setExibido] = useState(estado);
  useEffect(() => {
    setExibido(estado);
    if (!PASSAGEIRAS.has(estado)) return;
    const t = setTimeout(() => setExibido("ocioso"), 4000);
    return () => clearTimeout(t);
  }, [estado, chave]);
  return exibido;
}

/**
 * O Professor NTA acompanhando a conversa.
 * variante "lateral": corpo inteiro ao lado do chat (telas grandes)
 * variante "compacto": só a cabeça, junto da caixa de pergunta (celular e telas médias)
 * variante "inicio": grande, na tela inicial
 */
export default function Mascote({ estado, chave, variante = "lateral", saudacao }) {
  const ref = useRef(null);
  const mouse = useOlhar(ref);
  const exibido = useEstadoExibido(estado, chave);
  const olhar = exibido === "digitando" ? OLHAR_DIGITANDO[variante] : exibido === "pensando" ? { x: 0, y: -2.5 } : mouse;
  const fala = FALAS[exibido] || (variante === "inicio" ? saudacao : null);
  const [acenando, setAcenando] = useState(variante === "inicio");

  useEffect(() => {
    if (!acenando) return;
    const t = setTimeout(() => setAcenando(false), 2600);
    return () => clearTimeout(t);
  }, [acenando]);

  const robo = (
    <button
      type="button"
      ref={ref}
      onClick={() => setAcenando(true)}
      tabIndex={-1}
      aria-hidden="true"
      className="block cursor-pointer focus:outline-none"
    >
      <Robo
        estado={exibido}
        olhar={olhar}
        corpo={variante !== "compacto"}
        acenando={acenando}
        className={variante === "inicio" ? "h-40 w-auto sm:h-48" : variante === "lateral" ? "h-36 w-auto" : "size-11"}
      />
    </button>
  );

  if (variante === "compacto") {
    return (
      <div className="relative flex h-full shrink-0 flex-col justify-end" aria-hidden="true">
        {robo}
        {FALAS[exibido] && (
          <div className="balao absolute bottom-full left-0 mb-2 w-max max-w-[60vw] rounded-2xl rounded-bl-sm bg-marca-900 px-3 py-1.5 text-xs font-medium text-white shadow-lg dark:bg-slate-800">
            {FALAS[exibido]}
          </div>
        )}
      </div>
    );
  }

  if (variante === "inicio") {
    return (
      <div className="flex flex-col items-center" aria-hidden="true">
        {fala && (
          <div
            key={exibido}
            className="balao relative mb-3 rounded-2xl bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-md ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700"
          >
            {fala}
            <span className="absolute -bottom-1.5 left-1/2 size-3 -translate-x-1/2 rotate-45 bg-white dark:bg-slate-800" />
          </div>
        )}
        {robo}
      </div>
    );
  }

  // lateral: fixo no canto, fora da coluna do chat
  return (
    <div className="pointer-events-none fixed right-6 bottom-28 z-10 hidden flex-col items-end lg:flex xl:right-12" aria-hidden="true">
      {fala && (
        <div
          key={exibido}
          className="balao pointer-events-auto relative mb-2 max-w-52 rounded-2xl rounded-br-sm bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-lg ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700"
        >
          {fala}
        </div>
      )}
      <div className="pointer-events-auto">{robo}</div>
    </div>
  );
}
