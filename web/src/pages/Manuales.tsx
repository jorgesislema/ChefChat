import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BotonCargar } from "../components/BotonCargar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, Printer } from "lucide-react";
import { api, type CargaManual } from "../lib/api";
import { Button, Cargando, Card, ErrorCaja, Pagina, Vacio, cx } from "../components/ui/ui";

export default function Manuales() {
  const lista = useQuery({ queryKey: ["manuales"], queryFn: api.manuales });
  const [sel, setSel] = useState<number | null>(null);
  const id = sel ?? lista.data?.manuales[0]?.id ?? null;
  const manual = useQuery({ queryKey: ["manual", id], queryFn: () => api.manual(id as number), enabled: id !== null });

  const qc = useQueryClient();
  const cargar = (
    <BotonCargar<CargaManual>
      etiqueta="Cargar manual" aceptar=".md,.txt,.docx,.pdf" ayuda="Word, PDF, texto o Markdown. Hasta 5 MB."
      subir={api.cargarManual}
      alTerminar={() => { setSel(null); void qc.invalidateQueries({ queryKey: ["manuales"] }); void qc.invalidateQueries({ queryKey: ["manual"] }); void qc.invalidateQueries({ queryKey: ["temas"] }); }}
      resumen={(c) => (
        <p className="font-medium">
          {c.archivo}: {c.reemplazo ? "actualizado" : "cargado"} ({c.caracteres.toLocaleString("es")} letras). El asistente ya puede responder con él.
        </p>
      )}
    />
  );
  return (
    <Pagina titulo="Manuales" subtitulo="Lee e imprime los manuales de capacitación del equipo." accion={cargar}>
      {lista.error ? <ErrorCaja error={lista.error} onReintentar={() => lista.refetch()} /> : null}
      {lista.isLoading ? <Cargando /> : null}
      {lista.data && lista.data.manuales.length === 0 ? (
        <Vacio titulo="Aún no hay manuales" texto="Cuando cargues manuales en el sistema, aparecerán aquí." />
      ) : null}
      {lista.data && lista.data.manuales.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <nav aria-label="Lista de manuales" className="no-print space-y-2">
            {lista.data.manuales.map((m) => (
              <button key={m.id} onClick={() => setSel(m.id)} aria-current={m.id === id}
                className={cx("flex w-full items-start gap-3 rounded-xl border p-3 text-left transition",
                  m.id === id ? "border-brand bg-brand/10" : "border-line bg-surface hover:border-brand")}>
                <FileText size={20} className="mt-0.5 shrink-0 text-brand" aria-hidden />
                <span className="font-medium">{m.nombre.replace(/\.(md|txt)$/i, "")}</span>
              </button>
            ))}
          </nav>
          <Card className="print-area min-w-0">
            {manual.isLoading && <Cargando filas={6} />}
            {manual.error ? <ErrorCaja error={manual.error} onReintentar={() => manual.refetch()} /> : null}
            {manual.data && (
              <>
                <div className="no-print mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold">{manual.data.nombre.replace(/\.(md|txt)$/i, "")}</h2>
                  <Button variante="primario" onClick={() => window.print()}><Printer size={16} aria-hidden /> Imprimir</Button>
                </div>
                <h1 className="mb-4 hidden text-2xl font-bold print:block">{manual.data.nombre.replace(/\.(md|txt)$/i, "")}</h1>
                <div className="md">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{manual.data.texto.replace(/^---\n[\s\S]*?\n---\n/, "")}</ReactMarkdown>
                </div>
              </>
            )}
          </Card>
        </div>
      )}
    </Pagina>
  );
}
