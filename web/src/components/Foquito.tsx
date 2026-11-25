import { Lightbulb } from "lucide-react";

/** Foquito de aviso: queda 1 día o menos. Pista para que el chef lo use en el servicio de mañana. */
export function Foquito({ dias, tipo }: { dias: number; tipo?: "alimento" | "limpieza" }) {
  if (tipo === "limpieza" || dias < 0 || dias > 1) return null; // solo alimentos
  const texto = dias === 0 ? "Vence hoy: úsalo hoy" : "Vence mañana: úsalo en el servicio de mañana";
  return (
    <span title={texto} aria-label={texto} role="img" className="inline-flex shrink-0 text-warn">
      <Lightbulb size={18} aria-hidden fill="currentColor" fillOpacity={0.25} />
    </span>
  );
}
