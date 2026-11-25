import { describe, expect, it } from "vitest";
import { anchoBarra, atajosFechas, etiquetaParcial, fechaISO, leerDolares, nivelMargen, textoPct, textoPeriodo } from "./analisis";

describe("atajosFechas", () => {
  const a = atajosFechas(new Date(2026, 10, 25));
  it("Todo deja las fechas vacías", () => {
    expect(a[0]).toMatchObject({ id: "todo", desde: "", hasta: "" });
  });
  it("Últimos 30 días incluye hoy y cruza de mes", () => {
    expect(a[1]).toMatchObject({ desde: "2026-10-27", hasta: "2026-11-25" });
  });
  it("Últimos 90 días cruza de año cuando hace falta", () => {
    expect(atajosFechas(new Date(2026, 1, 10))[2]).toMatchObject({ desde: "2025-11-13", hasta: "2026-02-10" });
  });
  it("fechaISO rellena con ceros", () => {
    expect(fechaISO(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("textoPeriodo", () => {
  it("rango dentro del mismo año", () => {
    expect(textoPeriodo({ desde: "2026-04-19", hasta: "2026-05-19" })).toBe("Datos del 19 abr al 19 may 2026");
  });
  it("mismo día", () => {
    expect(textoPeriodo({ desde: "2026-04-19", hasta: "2026-04-19" })).toBe("Datos del 19 abr 2026");
  });
  it("años distintos", () => {
    expect(textoPeriodo({ desde: "2025-12-30", hasta: "2026-01-02" })).toBe("Datos del 30 dic 2025 al 2 ene 2026");
  });
  it("sin datos o fechas nulas", () => {
    expect(textoPeriodo(null)).toBe("No hay datos en estas fechas");
    expect(textoPeriodo({ desde: null, hasta: null })).toBe("No hay datos en estas fechas");
    expect(textoPeriodo({ desde: "2026-04-19", hasta: null })).toBe("No hay datos en estas fechas");
  });
});

describe("anchoBarra", () => {
  it("proporción normal", () => expect(anchoBarra(25, 100)).toBe(25));
  it("máximo cero no divide", () => expect(anchoBarra(5, 0)).toBe(0));
  it("valor negativo, NaN o cero da 0", () => {
    expect(anchoBarra(-3, 10)).toBe(0);
    expect(anchoBarra(NaN, 10)).toBe(0);
    expect(anchoBarra(0, 10)).toBe(0);
  });
  it("no pasa de 100", () => expect(anchoBarra(150, 100)).toBe(100));
});

describe("nivelMargen", () => {
  it("clasifica por umbrales", () => {
    expect(nivelMargen(60)).toBe("ok");
    expect(nivelMargen(59.9)).toBe("warn");
    expect(nivelMargen(30)).toBe("warn");
    expect(nivelMargen(29.9)).toBe("bad");
    expect(nivelMargen(-5)).toBe("bad");
  });
  it("sin dato devuelve null", () => {
    expect(nivelMargen(null)).toBeNull();
    expect(nivelMargen(undefined)).toBeNull();
  });
});

describe("etiquetaParcial", () => {
  it("marca meses con menos de 20 días", () => {
    expect(etiquetaParcial(19)).toBe("datos parciales (19 días)");
    expect(etiquetaParcial(1)).toBe("datos parciales (1 día)");
  });
  it("mes completo no lleva etiqueta", () => {
    expect(etiquetaParcial(20)).toBeNull();
    expect(etiquetaParcial(30)).toBeNull();
  });
});

describe("textoPct y leerDolares", () => {
  it("formatea porcentajes con coma", () => {
    expect(textoPct(12.54)).toBe("12,5 %");
    expect(textoPct(null)).toBe("-");
  });
  it("lee dólares con coma o punto", () => {
    expect(leerDolares("12,50")).toBe(12.5);
    expect(leerDolares(" 3 ")).toBe(3);
    expect(leerDolares("")).toBeUndefined();
    expect(leerDolares("abc")).toBeNull();
    expect(leerDolares("-4")).toBeNull();
    expect(leerDolares("200000")).toBeNull();
  });
});
