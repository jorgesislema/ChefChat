import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Balance } from "./Balance";
import type { Balance as DatosBalance } from "../../lib/api";

const foto: DatosBalance = {
  fecha: "2026-11-25", turno: "matutino", estado: "alarma",
  kg: { entregado: 100, devuelto: 0, entro: 100, salio_bueno: 70, perdida_normal: 5, merma: 1, comida_personal: 0, residuo_limpieza: 0, muestra: 0, otro: 0, anotado: 1, sin_explicar: 24 },
  sin_explicar_pct: 24, tolerancia_pct: 2, costo_kg: 3, sin_explicar_dinero: 72,
  por_ingrediente: [], por_plato: [], unidades: { producido: 0, vendido: 0, recibido: null, perdidas: null },
  movimientos: [], salidas: [], mermas: [], mensajes: ["Faltan 24,0 kg sin explicar."], avisos: [],
};

describe("Balance", () => {
  it("muestra el semáforo de alarma y el mensaje del servidor, sin botones si está firmado", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <Balance fecha={foto.fecha} turno={foto.turno} firmado congelado={foto} />
      </QueryClientProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Alarma");
    expect(screen.getByText("Faltan 24,0 kg sin explicar.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrega de bodega" })).not.toBeInTheDocument();
  });
});
