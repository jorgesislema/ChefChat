import { useSyncExternalStore } from "react";
import { api } from "./api";
import { MSG_SIN_CONEXION } from "./api";

export interface Mensaje { id: number; rol: "user" | "bot"; texto: string; error?: boolean; pregunta?: string }
interface Estado { mensajes: Mensaje[]; esperando: boolean; abierto: boolean }

let estado: Estado = { mensajes: [], esperando: false, abierto: false };
let sig = 1;
const oyentes = new Set<() => void>();
const poner = (e: Partial<Estado>) => {
  estado = { ...estado, ...e };
  oyentes.forEach((f) => f());
};

/** La conversación vive aquí (fuera de React) para no perderse al cambiar de pantalla. */
export async function enviar(texto: string, reintento?: number): Promise<void> {
  const t = texto.trim();
  if (!t || estado.esperando) return;
  let mensajes = estado.mensajes;
  if (reintento !== undefined) mensajes = mensajes.filter((m) => m.id !== reintento);
  else mensajes = [...mensajes, { id: sig++, rol: "user", texto: t }];
  poner({ mensajes, esperando: true });
  let nuevo: Mensaje;
  try {
    const r = await api.chat(t);
    nuevo = { id: sig++, rol: "bot", texto: r.respuesta, error: !!r.error, pregunta: t };
  } catch (e) {
    const sinRed = e instanceof Error && e.message === MSG_SIN_CONEXION;
    nuevo = {
      id: sig++, rol: "bot", error: true, pregunta: t,
      texto: sinRed ? MSG_SIN_CONEXION : "No pude responder ahora. Intenta de nuevo en un momento.",
    };
  }
  poner({ mensajes: [...estado.mensajes, nuevo], esperando: false });
}

/** Abre la burbuja del asistente; si trae una pregunta, la envia. */
export function abrirChat(pregunta?: string): void {
  poner({ abierto: true });
  if (pregunta) void enviar(pregunta);
}
export const cerrarChat = () => poner({ abierto: false });

export const reintentar = (m: Mensaje) => (m.pregunta ? enviar(m.pregunta, m.id) : Promise.resolve());

export const useChat = () =>
  useSyncExternalStore(
    (f) => { oyentes.add(f); return () => { oyentes.delete(f); }; },
    () => estado,
  );
