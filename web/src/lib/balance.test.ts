import { describe, expect, it } from "vitest";
import { colorEstado, etiquetaEstado, kg, pct, tramosBarra } from "./balance";
import type { KgBalance } from "./api";

const base: KgBalance = {
  entregado: 100, devuelto: 0, entro: 100, salio_bueno: 70, perdida_normal: 10, merma: 2, comida_personal: 2, residuo_limpieza: 1,
  muestra: 0, otro: 0, anotado: 5, sin_explicar: 15,
};

describe("kg", () => {
  it("usa coma y un decimal", () => { expect(kg(12.34)).toBe("12,3 kg"); expect(kg(0)).toBe("0,0 kg"); });
  it("no escribe -0,0", () => expect(kg(-0.01)).toBe("0,0 kg"));
  it("acepta null", () => expect(kg(null)).toBe("0,0 kg"));
});

describe("pct", () => {
  it("formatea y maneja null", () => { expect(pct(3.26)).toBe("3,3 %"); expect(pct(null)).toBe("—"); });
});

describe("estado", () => {
  it("etiquetas en español simple", () => {
    expect(etiquetaEstado("bien")).toBe("Bien");
    expect(etiquetaEstado("cerca")).toBe("Cerca del límite");
    expect(etiquetaEstado("alarma")).toBe("Alarma");
    expect(etiquetaEstado("sin_entregas")).toBe("Sin entregas de bodega");
  });
  it("colores", () => {
    expect(colorEstado("bien").punto).toBe("bg-ok");
    expect(colorEstado("cerca").punto).toBe("bg-warn");
    expect(colorEstado("alarma").punto).toBe("bg-bad");
    expect(colorEstado("sin_datos").punto).toBe("bg-muted");
  });
});

describe("tramosBarra", () => {
  it("reparte lo que entró en porcentajes", () => {
    const t = tramosBarra(base);
    expect(t.map((x) => x.pct)).toEqual([70, 10, 5, 15]);
  });
  it("sin tramo de sin explicar cuando sobra", () => {
    const t = tramosBarra({ ...base, sin_explicar: -4 });
    expect(t.find((x) => x.clave === "sin_explicar")?.kg).toBe(0);
  });
  it("vacío si no entró nada", () => expect(tramosBarra({ ...base, entro: 0 })).toEqual([]));
  it("nunca pasa de 100 %", () => {
    const t = tramosBarra({ ...base, entro: 50 });
    expect(t.reduce((s, x) => s + x.pct, 0)).toBeCloseTo(100);
  });
});
