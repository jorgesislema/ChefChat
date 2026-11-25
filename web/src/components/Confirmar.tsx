import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button, Dialogo } from "./ui/ui";

interface Props {
  titulo: string;
  /** Qué va a pasar, en palabras simples */
  texto: string;
  /** Texto del botón que confirma, por ejemplo «Sí, quitar» */
  confirmar: string;
  /** Se ejecuta al confirmar. Si falla, el mensaje del servidor se muestra aquí y el diálogo sigue abierto. */
  alConfirmar: () => Promise<unknown>;
  alCerrar: () => void;
  /** Una línea que dice cómo deshacerlo (o que no se puede) */
  deshacer?: string;
}

/** Confirmación para acciones que quitan algo. Nunca borra sin que el usuario lo pida. */
export function Confirmar({ titulo, texto, confirmar, alConfirmar, alCerrar, deshacer }: Props) {
  const [trabajando, setTrabajando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ejecutar = async () => {
    setTrabajando(true);
    setError(null);
    try {
      await alConfirmar();
      alCerrar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude hacerlo. Intenta de nuevo.");
      setTrabajando(false);
    }
  };

  return (
    <Dialogo titulo={titulo} onCerrar={alCerrar}>
      <div className="space-y-4">
        <p className="flex gap-2"><AlertTriangle className="mt-0.5 shrink-0 text-warn" size={18} aria-hidden /> <span>{texto}</span></p>
        {deshacer && <p className="text-sm text-muted">{deshacer}</p>}
        {error && <p role="alert" className="rounded-xl border border-bad/50 bg-bad/10 p-3 text-sm text-bad">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button onClick={alCerrar} disabled={trabajando}>Cancelar</Button>
          <Button variante="peligro" onClick={() => void ejecutar()} disabled={trabajando}>
            {trabajando && <Loader2 size={14} className="animate-spin" aria-hidden />} {confirmar}
          </Button>
        </div>
      </div>
    </Dialogo>
  );
}
