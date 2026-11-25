import { useRef, useState, type ReactNode } from "react";
import { CheckCircle2, Loader2, Upload, X } from "lucide-react";
import { Button, Card } from "./ui/ui";

interface Props<T> {
  etiqueta: string;
  /** Extensiones que acepta el selector de archivos, por ejemplo ".csv" */
  aceptar: string;
  /** Texto corto que explica qué archivo sirve */
  ayuda: string;
  subir: (archivo: File) => Promise<T>;
  /** Mensaje de éxito a partir de la respuesta del servidor */
  resumen: (r: T) => ReactNode;
  /** Qué hacer al terminar bien (por ejemplo, refrescar la lista) */
  alTerminar?: (r: T) => void;
}

/** Botón para subir un archivo. Muestra el avance, el resultado y los errores en palabras simples. */
export function BotonCargar<T>({ etiqueta, aceptar, ayuda, subir, resumen, alTerminar }: Props<T>) {
  const entrada = useRef<HTMLInputElement>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hecho, setHecho] = useState<ReactNode>(null);
  const [abierto, setAbierto] = useState(false);

  const elegir = async (archivo: File | undefined) => {
    if (!archivo) return;
    setCargando(true);
    setError(null);
    setHecho(null);
    setAbierto(true);
    try {
      const r = await subir(archivo);
      setHecho(resumen(r));
      alTerminar?.(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No pude cargar el archivo.");
    } finally {
      setCargando(false);
      if (entrada.current) entrada.current.value = ""; // permite volver a elegir el mismo archivo
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <input ref={entrada} type="file" accept={aceptar} className="sr-only" tabIndex={-1} aria-label={etiqueta}
        onChange={(e) => void elegir(e.target.files?.[0])} />
      <Button variante="primario" disabled={cargando} onClick={() => entrada.current?.click()} aria-describedby="ayuda-carga">
        {cargando ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Upload size={16} aria-hidden />} {etiqueta}
      </Button>
      <span id="ayuda-carga" className="text-xs text-muted">{ayuda}</span>
      {abierto && (cargando || error || hecho) && (
        <Card role={error ? "alert" : "status"} className={`relative w-full max-w-md text-sm ${error ? "border-bad/50" : "border-ok/50"}`}>
          <button onClick={() => setAbierto(false)} aria-label="Cerrar el aviso" className="absolute right-2 top-2 rounded-lg p-1 text-muted hover:bg-line/50"><X size={14} /></button>
          {cargando && <p className="flex items-center gap-2"><Loader2 size={16} className="animate-spin" aria-hidden /> Cargando y revisando el archivo…</p>}
          {error && <p className="pr-6 text-bad">{error}</p>}
          {hecho && <div className="flex gap-2 pr-6"><CheckCircle2 size={18} className="mt-0.5 shrink-0 text-ok" aria-hidden /><div>{hecho}</div></div>}
        </Card>
      )}
    </div>
  );
}
