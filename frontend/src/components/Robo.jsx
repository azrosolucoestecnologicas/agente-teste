import { useId } from "react";

// O Professor NTA: robô em azul, vermelho e prata, desenhado em SVG (sem imagem externa).
// estado: ocioso | digitando | pensando | escrevendo | feliz | confuso | triste | limite
// olhar: deslocamento dos olhos, em pixels do desenho ({x, y}, até ~4)
// corpo: false desenha só a cabeça (avatar e versão compacta)
export default function Robo({ estado = "ocioso", olhar = { x: 0, y: 0 }, corpo = true, acenando = false, className = "" }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const prata = `prata${id}`;
  const azul = `azul${id}`;
  const brilho = `brilho${id}`;

  const feliz = estado === "feliz";
  const triste = estado === "triste" || estado === "limite";
  const confuso = estado === "confuso";
  const pensando = estado === "pensando";
  const falando = estado === "escrevendo";

  return (
    <svg
      viewBox={corpo ? "0 0 120 156" : "12 0 96 86"}
      className={`robo robo-${estado} ${className}`}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={prata} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f8fafc" />
          <stop offset="0.55" stopColor="#cbd5e1" />
          <stop offset="1" stopColor="#94a3b8" />
        </linearGradient>
        <linearGradient id={azul} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2563eb" />
          <stop offset="1" stopColor="#1e3a8a" />
        </linearGradient>
        <radialGradient id={brilho}>
          <stop offset="0" stopColor="#fecaca" />
          <stop offset="0.5" stopColor="#ef4444" />
          <stop offset="1" stopColor="#b91c1c" />
        </radialGradient>
      </defs>

      {corpo && <ellipse className="robo-sombra" cx="60" cy="150" rx="24" ry="4" fill="#0f172a" opacity="0.15" />}

      <g className={corpo ? "robo-flutua" : ""}>
        {corpo && (
          <g>
            {/* braço esquerdo */}
            <rect x="15" y="92" width="12" height="28" rx="6" fill={`url(#${prata})`} stroke="#94a3b8" />
            <circle cx="21" cy="122" r="5.5" fill="#dc2626" />
            {/* braço direito: acena */}
            <g className={acenando || feliz ? "robo-aceno" : ""} style={{ transformBox: "fill-box", transformOrigin: "50% 8%" }}>
              <rect x="93" y="92" width="12" height="28" rx="6" fill={`url(#${prata})`} stroke="#94a3b8" />
              <circle cx="99" cy="122" r="5.5" fill="#dc2626" />
            </g>
            {/* pescoço, tronco e base */}
            <rect x="52" y="78" width="16" height="9" rx="3" fill="#94a3b8" />
            <rect x="28" y="85" width="64" height="46" rx="16" fill={`url(#${azul})`} />
            <rect x="34" y="88" width="52" height="6" rx="3" fill="#ffffff" opacity="0.18" />
            <rect x="45" y="97" width="30" height="22" rx="7" fill={`url(#${prata})`} stroke="#94a3b8" />
            <circle className="robo-coracao" cx="60" cy="108" r="5.5" fill={`url(#${brilho})`} />
            <rect x="44" y="131" width="32" height="9" rx="4.5" fill={`url(#${prata})`} stroke="#94a3b8" />
            <rect x="50" y="140" width="20" height="3" rx="1.5" fill="#ef4444" opacity="0.7" className="robo-jato" />
          </g>
        )}

        {/* cabeça (inclina quando confuso) */}
        <g className="robo-cabeca" style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}>
          <line x1="60" y1="24" x2="60" y2="10" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
          <circle className="robo-antena" cx="60" cy="8" r="5.5" fill={`url(#${brilho})`} />
          <circle cx="19" cy="51" r="6.5" fill="#dc2626" />
          <circle cx="101" cy="51" r="6.5" fill="#dc2626" />
          <rect x="22" y="22" width="76" height="58" rx="18" fill={`url(#${prata})`} stroke="#94a3b8" />
          <rect x="28" y="26" width="40" height="5" rx="2.5" fill="#ffffff" opacity="0.7" />
          <rect x="30" y="33" width="60" height="38" rx="13" fill="#0b1f4b" />

          {/* olhos */}
          <g style={{ transform: `translate(${olhar.x}px, ${olhar.y}px)`, transition: "transform 160ms ease-out" }}>
            <g className={pensando ? "robo-varre" : ""}>
              {feliz ? (
                <g fill="none" stroke="#7dd3fc" strokeWidth="3.2" strokeLinecap="round">
                  <path d="M41 51 Q47 43 53 51" />
                  <path d="M67 51 Q73 43 79 51" />
                </g>
              ) : (
                <g className="robo-olhos" style={{ transformBox: "fill-box", transformOrigin: "50% 50%" }} fill="#7dd3fc">
                  <circle cx="47" cy="49" r={triste ? 4.5 : 6} />
                  <circle cx="73" cy="49" r={confuso ? 4 : triste ? 4.5 : 6} />
                  {!triste && (
                    <g fill="#ffffff">
                      <circle cx="49" cy="47" r="1.8" />
                      <circle cx="75" cy="47" r={confuso ? 1.3 : 1.8} />
                    </g>
                  )}
                </g>
              )}
            </g>
          </g>
          {triste && (
            <g stroke="#7dd3fc" strokeWidth="2" strokeLinecap="round">
              <line x1="41" y1="41" x2="51" y2="44" />
              <line x1="79" y1="41" x2="69" y2="44" />
            </g>
          )}
          {confuso && (
            <line x1="68" y1="40" x2="78" y2="38" stroke="#7dd3fc" strokeWidth="2" strokeLinecap="round" />
          )}

          {/* boca */}
          <g className={falando ? "robo-fala" : ""} style={{ transformBox: "fill-box", transformOrigin: "50% 50%" }}>
            {falando ? (
              <rect x="53" y="59" width="14" height="6" rx="3" fill="#7dd3fc" />
            ) : triste ? (
              <path d="M52 65 Q60 59 68 65" fill="none" stroke="#7dd3fc" strokeWidth="2.5" strokeLinecap="round" />
            ) : confuso ? (
              <path d="M51 62 Q55 59 59 62 T67 62" fill="none" stroke="#7dd3fc" strokeWidth="2.5" strokeLinecap="round" />
            ) : (
              <path d={feliz ? "M50 59 Q60 69 70 59" : "M52 61 Q60 66 68 61"} fill="none" stroke="#7dd3fc" strokeWidth="2.5" strokeLinecap="round" />
            )}
          </g>
        </g>
      </g>
    </svg>
  );
}
