import { describe, expect, it } from "vitest";
import type { LineaConteo } from "./api";
import {
  agruparPorCategoria, avancePct, cuerpoContar, diferencia, filaUsado, filtrarLineas, leerCantidad, nivelDiferencia,
  resumenCierre, textoCantidad, textoDiferencia,
} from "./conteo";

const l = (id: number, producto: string, sistema: number, contada: number | null, categoria: string | null = "Lácteos", valor: number | null = 10): LineaConteo => ({
  id, conteo_id: 1, producto_id: id, producto, categoria, tipo: "alimento", unidad: "kg", cantidad_sistema: sistema, cantidad_contada: contada,
  precio: 2, valor_sistema: valor, valor_contado: null, diferencia: null, diferencia_pct: null, valor_diferencia: null,
});
const lineas = [l(1, "Queso", 5, 5), l(2, "Leche", 10, 8), l(3, "Arroz", 20, null, "Granos"), l(4, "Sal", 1, 2, null)];

describe("leerCantidad", () => {
  it("acepta coma y punto", () => {
    expect(leerCantidad("2,5")).toBe(2.5);
    expect(leerCantidad(" 3.25 ")).toBe(3.25);
    expect(leerCantidad("0")).toBe(0);
  });
  it("vacío es sin contar (null)", () => {
    expect(leerCantidad("")).toBeNull();
    expect(leerCantidad("   ")).toBeNull();
  });
  it("lo inválido da NaN", () => {
    expect(leerCantidad("abc")).toBeNaN();
    expect(leerCantidad("-1")).toBeNaN();
    expect(leerCantidad("1,2,3")).toBeNaN();
  });
});

describe("textoCantidad", () => {
  it("usa coma decimal y deja vacío lo no contado", () => {
    expect(textoCantidad(2.5)).toBe("2,5");
    expect(textoCantidad(0)).toBe("0");
    expect(textoCantidad(null)).toBe("");
  });
});

describe("diferencia y nivel", () => {
  it("calcula la diferencia", () => {
    expect(diferencia(10, 8)).toBe(-2);
    expect(diferencia(0.3, 0.1)).toBe(-0.2);
    expect(diferencia(10, null)).toBeNull();
  });
  it("falta rojo, sobra ámbar, igual verde", () => {
    expect(nivelDiferencia(-2)).toEqual({ nivel: "bad", texto: "Falta" });
    expect(nivelDiferencia(1)).toEqual({ nivel: "warn", texto: "Sobra" });
    expect(nivelDiferencia(0)).toEqual({ nivel: "ok", texto: "Igual" });
    expect(nivelDiferencia(null)).toBeNull();
  });
  it("texto con signo", () => {
    expect(textoDiferencia(1.5)).toBe("+1,5");
    expect(textoDiferencia(-2)).toBe("-2");
    expect(textoDiferencia(0)).toBe("0");
  });
});

describe("avancePct", () => {
  it("redondea y cuida el cero", () => {
    expect(avancePct(34, 120)).toBe(28);
    expect(avancePct(0, 0)).toBe(0);
    expect(avancePct(5, 5)).toBe(100);
  });
});

describe("filtrarLineas", () => {
  it("sin contar", () => expect(filtrarLineas(lineas, { chip: "sin_contar" }).map((x) => x.producto)).toEqual(["Arroz"]));
  it("con diferencia", () => expect(filtrarLineas(lineas, { chip: "con_diferencia" }).map((x) => x.producto)).toEqual(["Leche", "Sal"]));
  it("por nombre y categoría", () => {
    expect(filtrarLineas(lineas, { q: " LEC" }).map((x) => x.producto)).toEqual(["Leche"]);
    expect(filtrarLineas(lineas, { categoria: "Granos" }).map((x) => x.producto)).toEqual(["Arroz"]);
    expect(filtrarLineas(lineas, { chip: "todos" })).toHaveLength(4);
  });
});

describe("cuerpoContar", () => {
  it("envía solo lo que cambió", () => {
    const r = cuerpoContar(lineas, { 1: "5", 2: "9,5", 3: "" });
    expect(r.cambios).toEqual([{ producto_id: 2, cantidad: 9.5 }]);
    expect(r.invalidos).toBe(0);
  });
  it("vaciar un campo ya contado lo borra (null)", () => {
    expect(cuerpoContar(lineas, { 2: "" }).cambios).toEqual([{ producto_id: 2, cantidad: null }]);
  });
  it("no envía números inválidos y los cuenta", () => {
    const r = cuerpoContar(lineas, { 3: "x", 4: "3" });
    expect(r.cambios).toEqual([{ producto_id: 4, cantidad: 3 }]);
    expect(r.invalidos).toBe(1);
  });
});

describe("agruparPorCategoria", () => {
  it("ordena categorías y deja «Sin categoría» al final", () => {
    const g = agruparPorCategoria(lineas);
    expect(g.map((x) => x.categoria)).toEqual(["Granos", "Lácteos", "Sin categoría"]);
    expect(g[1].lineas.map((x) => x.producto)).toEqual(["Leche", "Queso"]);
  });
});

describe("resumenCierre", () => {
  it("suma lo del sistema para lo no contado solo si se pide", () => {
    expect(resumenCierre(lineas, 40, 25, false)).toEqual({ sinContar: 1, sistema: 40, contado: 25, diferencia: -15 });
    expect(resumenCierre(lineas, 40, 25, true)).toEqual({ sinContar: 1, sistema: 40, contado: 35, diferencia: -5 });
  });
});

describe("filaUsado", () => {
  const base = { metodo: "conteo" as const, comprado: 300, real: 500, inventario_inicial: { id: 1, fecha: "2026-01-31", valor: 400 }, inventario_final: { id: 2, fecha: "2026-02-28", valor: 200 } };
  it("inicial + compras - final = usado", () => {
    const f = filaUsado(base);
    expect(f).toMatchObject({ inicial: 400, comprado: 300, final: 200, usado: 500, fechaInicial: "2026-01-31", fechaFinal: "2026-02-28" });
    expect(f!.inicial + f!.comprado - f!.final).toBe(f!.usado);
  });
  it("sin método conteo o sin un inventario no hay fila", () => {
    expect(filaUsado({ ...base, metodo: "compras" })).toBeNull();
    expect(filaUsado({ ...base, inventario_final: null })).toBeNull();
  });
});
