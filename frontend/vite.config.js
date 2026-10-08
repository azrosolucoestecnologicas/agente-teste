import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Em desenvolvimento (npm run dev), o Vite repassa /api para o servidor FastAPI na porta 8000.
// Em produção, o próprio servidor entrega o front-end e a API no mesmo endereço.
export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
