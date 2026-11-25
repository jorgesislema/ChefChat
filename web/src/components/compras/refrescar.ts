import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRefrescar } from "../edicion/comun";

/** Vuelve a pedir lo que una compra cambia: compras, análisis (costo real), inventario, lotes, proveedores y precios. */
export function useRefrescarCompras() {
  const qc = useQueryClient();
  const refrescar = useRefrescar();
  return useCallback(
    () => Promise.all([refrescar(), qc.invalidateQueries({ queryKey: ["compras"] }), qc.invalidateQueries({ queryKey: ["analisis"] })]),
    [qc, refrescar],
  );
}
