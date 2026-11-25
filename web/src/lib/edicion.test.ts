import { describe, expect, it } from "vitest";
import {
  aNumero, cuerpoEditaLote, cuerpoEditaProducto, cuerpoNuevoLote, fechaValida, hoyISO, textoDiferenciaPrecio,
  validarLote, validarProducto, type FormLote,
} from "./edicion";

const base: FormLote = { producto: "Tomate", cantidad: "5", unidad: "kg", fechaIngreso: "2026-03-10", vence: "", idLote: "", categoria: "" };

describe("textoDiferenciaPrecio", () => {
  it("dice si sube, baja o no cambia", () => {
    expect(textoDiferenciaPrecio(10, 11.2)).toBe("subirá 12 %");
    expect(textoDiferenciaPrecio(10, 9.2)).toBe("bajará 8 %");
    expect(textoDiferenciaPrecio(10, 10)).toBe("sin cambio");
  });
  it("usa coma decimal", () => {
    expect(textoDiferenciaPrecio(10, 10.25)).toBe("subirá 2,5 %");
  });
  it("devuelve vacío sin precio anterior", () => {
    expect(textoDiferenciaPrecio(null, 5)).toBe("");
    expect(textoDiferenciaPrecio(0, 5)).toBe("");
  });
});

describe("aNumero y fechas", () => {
  it("acepta coma y punto", () => {
    expect(aNumero("1,5")).toBe(1.5);
    expect(aNumero(" 2.25 ")).toBe(2.25);
    expect(aNumero("")).toBeNaN();
    expect(aNumero("abc")).toBeNaN();
  });
  it("valida fechas reales", () => {
    expect(fechaValida("2026-02-28")).toBe(true);
    expect(fechaValida("2026-02-30")).toBe(false);
    expect(fechaValida("10/03/2026")).toBe(false);
  });
  it("hoyISO usa la fecha local", () => {
    expect(hoyISO(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("validarLote", () => {
  it("acepta un lote correcto", () => {
    expect(validarLote(base)).toEqual([]);
  });
  it("pide producto y cantidad mayor que cero", () => {
    expect(validarLote({ ...base, producto: " ", cantidad: "0" })).toEqual([
      "Escribe el nombre del producto.", "La cantidad debe ser un número mayor que cero.",
    ]);
  });
  it("no pide producto al editar", () => {
    expect(validarLote({ ...base, producto: "" }, { editando: true })).toEqual([]);
  });
  it("rechaza vencimiento antes del ingreso", () => {
    expect(validarLote({ ...base, vence: "2026-03-01" })).toEqual(["El vencimiento no puede ser antes del ingreso."]);
  });
  it("rechaza fechas inválidas y unidad desconocida", () => {
    const m = validarLote({ ...base, fechaIngreso: "2026-13-01", vence: "ayer", unidad: "taza" });
    expect(m).toContain("La fecha de ingreso no es válida.");
    expect(m).toContain("La fecha de vencimiento no es válida.");
    expect(m).toContain("Elige una unidad.");
  });
  it("ignora el vencimiento si se usa la vida útil", () => {
    expect(validarLote({ ...base, vence: "basura", usarVidaUtil: true }, { editando: true })).toEqual([]);
  });
});

describe("cuerpos a enviar", () => {
  it("nuevo lote: omite lo vacío y manda categoría solo si el producto es nuevo", () => {
    expect(cuerpoNuevoLote({ ...base, categoria: "Verduras" }, true)).toEqual({
      producto: "Tomate", cantidad: 5, unidad: "kg", fecha_ingreso: "2026-03-10",
    });
    expect(cuerpoNuevoLote({ ...base, categoria: "Verduras", vence: "2026-03-20", idLote: " L1 " }, false)).toEqual({
      producto: "Tomate", cantidad: 5, unidad: "kg", fecha_ingreso: "2026-03-10", fecha_caducidad: "2026-03-20", id_lote: "L1", categoria: "Verduras",
    });
  });
  it("editar lote: quitar_caducidad reemplaza la fecha", () => {
    const f = { ...base, cantidad: "2,5", vence: "2026-04-01" };
    expect(cuerpoEditaLote(f)).toEqual({ cantidad: 2.5, unidad: "kg", fecha_ingreso: "2026-03-10", fecha_caducidad: "2026-04-01" });
    expect(cuerpoEditaLote({ ...f, usarVidaUtil: true })).toEqual({ cantidad: 2.5, unidad: "kg", fecha_ingreso: "2026-03-10", quitar_caducidad: true });
  });
});

describe("producto", () => {
  it("valida nombre y vida útil entera", () => {
    expect(validarProducto({ nombre: "", categoria: "", tipo: "alimento", vidaUtil: "2,5" })).toHaveLength(2);
    expect(validarProducto({ nombre: "Sal", categoria: "", tipo: "alimento", vidaUtil: "" })).toEqual([]);
  });
  it("arma el cuerpo sin campos vacíos", () => {
    expect(cuerpoEditaProducto({ nombre: " Sal ", categoria: "", tipo: "alimento", vidaUtil: "30" })).toEqual({ nombre: "Sal", tipo: "alimento", vida_util_dias: 30 });
  });
});
