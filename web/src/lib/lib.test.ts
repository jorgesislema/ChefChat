import { describe, expect, it } from "vitest";
import { listaATabla } from "./tabla";
import { diasRestantes, etiquetaDias, semaforo } from "./format";

describe("listaATabla", () => {
  it("convierte líneas '- a | lote b | c kg | vence d' en tabla", () => {
    const t = listaATabla("Vencen (2 lotes):\n- Leche | lote L1 | 5 L | vence 2026-12-01\n- Pollo | lote P2 | 3 kg | vence 2026-12-03\nFin");
    expect(t).toContain("| Producto | Lote | Cantidad | Vence |");
    expect(t).toContain("| Leche | L1 | 5 L | 2026-12-01 |");
    expect(t).toContain("| Pollo | P2 | 3 kg | 2026-12-03 |");
    expect(t).toContain("Vencen (2 lotes):");
    expect(t).toContain("Fin");
  });
  it("deja intacto el texto sin ese formato", () => {
    const s = "- una lista\n- normal\nhola";
    expect(listaATabla(s)).toBe(s);
  });
  it("no toca líneas con otro número de columnas", () => {
    const s = "- a | b | c";
    expect(listaATabla(s)).toBe(s);
  });
});

describe("días restantes", () => {
  const hoy = new Date(2026, 10, 24);
  it("calcula días", () => {
    expect(diasRestantes("2026-11-24", hoy)).toBe(0);
    expect(diasRestantes("2026-11-27", hoy)).toBe(3);
    expect(diasRestantes("2026-11-20", hoy)).toBe(-4);
  });
  it("etiqueta", () => {
    expect(etiquetaDias(5)).toBe("Vence en 5 días");
    expect(etiquetaDias(1)).toBe("Vence mañana");
    expect(etiquetaDias(0)).toBe("Vence hoy");
    expect(etiquetaDias(-3)).toBe("Venció hace 3 días");
  });
  it("semáforo: rojo <=3, ámbar <=10, verde resto", () => {
    expect([3, 4, 10, 11].map(semaforo)).toEqual(["bad", "warn", "warn", "ok"]);
  });
});

import { dinero as _d2, fechaEnFrase as _f2 } from "./format";
describe("formato de dinero y fechas", () => {
  it("negativos con el signo delante", () => { expect(_d2(-184.38)).toBe("-" + _d2(184.38)); expect(_d2(-184.38).startsWith("-$")).toBe(true); });
  it("fecha en minuscula dentro de una frase", () => { expect(_f2("2026-11-25")).toBe("miércoles, 25 de noviembre de 2026"); });
});
