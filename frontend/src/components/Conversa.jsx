import { useEffect, useRef } from "react";
import Mensagem from "./Mensagem.jsx";

export default function Conversa({ mensagens, aoTentarDeNovo }) {
  const fimRef = useRef(null);
  const areaRef = useRef(null);
  const ultima = mensagens[mensagens.length - 1];

  // Rola para o fim enquanto a resposta chega, a não ser que a pessoa tenha subido para reler
  useEffect(() => {
    const area = areaRef.current;
    if (!area) return;
    const pertoDoFim = area.scrollHeight - area.scrollTop - area.clientHeight < 160;
    if (pertoDoFim || ultima?.role === "user" || ultima?.status === "pensando") {
      fimRef.current?.scrollIntoView({ block: "end" });
    }
  }, [mensagens.length, ultima?.content, ultima?.status, ultima?.role]);

  return (
    <div ref={areaRef} className="flex-1 overflow-y-auto">
      <div role="log" aria-live="polite" aria-label="Conversa" className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
        {mensagens.map((m) => (
          <Mensagem key={m.id} mensagem={m} aoTentarDeNovo={() => aoTentarDeNovo(m.id)} />
        ))}
        <div ref={fimRef} />
      </div>
    </div>
  );
}
