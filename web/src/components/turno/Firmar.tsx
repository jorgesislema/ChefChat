import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "../ui/ui";
import { Campo, DialogoEdicion, campo } from "../edicion/comun";

/** Pide el nombre de quien firma y avisa que después no se puede cambiar. */
export function Firmar({ inicial, alFirmar, alCerrar }: { inicial: string; alFirmar: (nombre: string) => Promise<unknown>; alCerrar: () => void }) {
  const [nombre, setNombre] = useState(inicial);
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enviar = async () => {
    if (trabajando) return;
    if (!nombre.trim()) { setError("Escribe el nombre de quien firma."); return; }
    setTrabajando(true);
    setError(null);
    try {
      await alFirmar(nombre.trim());
      alCerrar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude firmar el informe. Intenta de nuevo.");
      setTrabajando(false);
    }
  };

  return (
    <DialogoEdicion titulo="Firmar y cerrar el informe" onCerrar={alCerrar}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); void enviar(); }}>
        <p className="flex gap-2"><AlertTriangle className="mt-0.5 shrink-0 text-warn" size={18} aria-hidden /> <span>Después de firmar ya no se puede cambiar.</span></p>
        <Campo id="firma-nombre" etiqueta="Nombre de quien firma">
          <input id="firma-nombre" className={campo} value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" />
        </Campo>
        {error && <p role="alert" className="rounded-xl border border-bad/50 bg-bad/10 p-3 text-sm text-bad">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" onClick={alCerrar} disabled={trabajando}>Cancelar</Button>
          <Button type="submit" variante="primario" disabled={trabajando}>
            {trabajando && <Loader2 size={14} className="animate-spin" aria-hidden />} Firmar y cerrar
          </Button>
        </div>
      </form>
    </DialogoEdicion>
  );
}
