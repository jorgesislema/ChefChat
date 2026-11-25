import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type DestinoSobrante, type Sobrante } from "../../lib/api";
import { Button, Dialogo, ErrorCaja } from "../ui/ui";
import { Confirmar } from "../Confirmar";
import { leerDolares } from "../../lib/analisis";

type Paso = null | "usado" | "botado" | "donado";

/** Botones para decir qué pasó con un sobrante. Al terminar refresca los sobrantes y el análisis. */
export function AccionesSobrante({ s }: { s: Sobrante }) {
  const qc = useQueryClient();
  const [paso, setPaso] = useState<Paso>(null);
  const [valor, setValor] = useState("");
  const m = useMutation({
    mutationFn: (v: { destino: DestinoSobrante; valor_estimado?: number }) => api.destinoSobrante(s.id, v),
    onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ["menu-sobrantes"] }), qc.invalidateQueries({ queryKey: ["analisis"] })]),
  });
  const cerrar = () => { setPaso(null); setValor(""); m.reset(); };
  const num = leerDolares(valor);
  const valorMal = num === null;
  const nombre = `${s.producto} (${String(s.cantidad).replace(".", ",")} ${s.unidad})`;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {s.vigente ? (
        <>
          <Button variante="primario" onClick={() => setPaso("usado")}>Lo usé</Button>
          <Button variante="peligro" onClick={() => setPaso("botado")}>Lo boté</Button>
          <Button onClick={() => setPaso("donado")}>Lo doné</Button>
        </>
      ) : (
        <Button variante="peligro" onClick={() => setPaso("botado")}>Marcar como botado</Button>
      )}

      {paso === "usado" && (
        <Dialogo titulo="Lo usé" onCerrar={cerrar}>
          <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); if (!valorMal) m.mutate({ destino: "reutilizado", valor_estimado: num }, { onSuccess: cerrar }); }}>
            <p>Vas a marcar <strong>{nombre}</strong> como reutilizado.</p>
            <div>
              <label htmlFor={`sob-valor-${s.id}`} className="mb-1 block text-sm font-medium">¿Cuánto vale lo que recuperaste? (opcional)</label>
              <div className="flex items-center gap-2">
                <span aria-hidden>$</span>
                <input id={`sob-valor-${s.id}`} inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Ej. 4,50"
                  aria-invalid={valorMal} className="w-32 rounded-xl border border-line bg-bg px-3 py-2" />
              </div>
              {valorMal && <p className="mt-1 text-xs text-bad">Escribe un monto en dólares, por ejemplo 4 o 4,50.</p>}
            </div>
            {m.error != null && <ErrorCaja error={m.error} />}
            <div className="flex justify-end gap-2">
              <Button type="button" onClick={cerrar}>Cancelar</Button>
              <Button type="submit" variante="primario" disabled={valorMal || m.isPending}>Guardar</Button>
            </div>
          </form>
        </Dialogo>
      )}
      {paso === "botado" && (
        <Confirmar titulo="Marcar como botado" texto={`¿Seguro que botaste ${nombre}? Quedará anotado como desperdicio.`} confirmar="Sí, lo boté"
          deshacer="Esto no se puede deshacer después." alCerrar={cerrar} alConfirmar={() => m.mutateAsync({ destino: "desperdicio" })} />
      )}
      {paso === "donado" && (
        <Confirmar titulo="Marcar como donado" texto={`¿Seguro que donaste ${nombre}? Quedará anotado como donación.`} confirmar="Sí, lo doné"
          deshacer="Esto no se puede deshacer después." alCerrar={cerrar} alConfirmar={() => m.mutateAsync({ destino: "donacion" })} />
      )}
    </div>
  );
}
