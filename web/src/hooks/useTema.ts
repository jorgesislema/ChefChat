import { useEffect, useState } from "react";

export function useTema() {
  const [oscuro, setOscuro] = useState(() => localStorage.getItem("tema") !== "claro");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", oscuro);
    localStorage.setItem("tema", oscuro ? "oscuro" : "claro");
  }, [oscuro]);
  return { oscuro, alternar: () => setOscuro((o) => !o) };
}
