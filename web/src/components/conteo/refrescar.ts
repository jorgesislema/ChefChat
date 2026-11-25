import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRefrescarCompras } from "../compras/refrescar";

/** Vuelve a pedir lo que un conteo cambia: sus listas, inventario, lotes, productos, análisis y compras. */
export function useRefrescarConteo() {
  const qc = useQueryClient();
  const resto = useRefrescarCompras();
  return useCallback(
    () => Promise.all([resto(), qc.invalidateQueries({ queryKey: ["conteos"] }), qc.invalidateQueries({ queryKey: ["conteo"] })]),
    [qc, resto],
  );
}
