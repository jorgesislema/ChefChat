import { describe, expect, it } from "vitest";
import { atajosCompras, convertirCantidad, partesBarra, totalCompra } from "./compras";
import { aNumero } from "./edicion";

describe("totalCompra", () => {
  it("2000 g a 9,50 por kg = 19", () => expect(totalCompra(2000, "g", 9.5, "kg")).toBe(19));
  it("500 ml a 4 por litro = 2", () => expect(totalCompra(500, "ml", 4, "l")).toBe(2));
  it("2 libras a 3 por kg", () => expect(totalCompra(2, "libra", 3, "kg")).toBe(2.72));
  it("1 quintal a 2 por kg", () => expect(totalCompra(1, "qq", 2, "kg")).toBe(90.72));
  it("unidades a precio por unidad", () => expect(totalCompra(12, "unidad", 0.25, "unidad")).toBe(3));
  it("unidades incompatibles dan null", () => {
    expect(totalCompra(500, "ml", 4, "kg")).toBeNull();
    expect(totalCompra(1, "kg", 4, "unidad")).toBeNull();
    expect(convertirCantidad(1, "caja", "kg")).toBeNull();
  });
  it("cantidad no numérica da null", () => expect(totalCompra(NaN, "kg", 1, "kg")).toBeNull());
});

describe("lectura de números con coma", () => {
  it("9,50 es 9.5 y vacío no es número", () => {
    expect(aNumero("9,50")).toBe(9.5);
    expect(aNumero("  ")).toBeNaN();
  });
  it("el total sale igual con coma", () => expect(totalCompra(2000, "g", aNumero("9,50"), "kg")).toBe(19));
});

describe("atajosCompras", () => {
  const a = atajosCompras(new Date(2026, 10, 25));
  it("Este mes empieza el día 1 y termina hoy", () => expect(a[0]).toMatchObject({ desde: "2026-11-01", hasta: "2026-11-25" }));
  it("30 días incluye hoy", () => expect(a[1]).toMatchObject({ desde: "2026-10-27", hasta: "2026-11-25" }));
  it("90 días cruza de año", () => expect(atajosCompras(new Date(2026, 1, 10))[2]).toMatchObject({ desde: "2025-11-13", hasta: "2026-02-10" }));
  it("Todo deja fechas vacías", () => expect(a[3]).toMatchObject({ desde: "", hasta: "" }));
});

describe("partesBarra", () => {
  it("los porcentajes suman 100", () => {
    const { partes, gastoMenor } = partesBarra({ vendido: 60, sobreproduccion: 15, merma_registrada: 5, sin_explicar: 20 });
    expect(partes).toHaveLength(4);
    expect(partes.reduce((s, p) => s + p.pct, 0)).toBeCloseTo(100);
    expect(partes[0].pct).toBeCloseTo(60);
    expect(gastoMenor).toBe(false);
  });
  it("omite los ceros", () => {
    const { partes } = partesBarra({ vendido: 10, sobreproduccion: 0, merma_registrada: 0, sin_explicar: 0 });
    expect(partes.map((p) => p.clave)).toEqual(["vendido"]);
    expect(partes[0].pct).toBeCloseTo(100);
  });
  it("sin explicar negativo no se dibuja y avisa", () => {
    const { partes, gastoMenor } = partesBarra({ vendido: 30, sobreproduccion: 10, merma_registrada: 0, sin_explicar: -5 });
    expect(partes.map((p) => p.clave)).toEqual(["vendido", "sobreproduccion"]);
    expect(partes.reduce((s, p) => s + p.pct, 0)).toBeCloseTo(100);
    expect(gastoMenor).toBe(true);
  });
  it("todo en cero no da partes ni NaN", () => {
    const { partes } = partesBarra({ vendido: 0, sobreproduccion: 0, merma_registrada: 0, sin_explicar: 0 });
    expect(partes).toEqual([]);
  });
});
