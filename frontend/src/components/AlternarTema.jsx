import { Moon, Sun } from "lucide-react";
import { useState } from "react";

export default function AlternarTema() {
  const [escuro, setEscuro] = useState(() => document.documentElement.classList.contains("dark"));

  const alternar = () => {
    const novo = !escuro;
    document.documentElement.classList.toggle("dark", novo);
    try {
      localStorage.setItem("tema", novo ? "escuro" : "claro");
    } catch {
      /* navegador sem localStorage: vale só nesta visita */
    }
    setEscuro(novo);
  };

  return (
    <button
      type="button"
      onClick={alternar}
      aria-label={escuro ? "Usar tema claro" : "Usar tema escuro"}
      title={escuro ? "Tema claro" : "Tema escuro"}
      className="grid size-10 place-items-center rounded-full text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {escuro ? <Sun className="size-5" aria-hidden="true" /> : <Moon className="size-5" aria-hidden="true" />}
    </button>
  );
}
