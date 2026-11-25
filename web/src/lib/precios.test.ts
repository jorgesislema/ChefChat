import { describe, expect, it } from "vitest";
import { cambioPrecio, nivelMargen, precioConUnidad } from "./precios";

describe("precioConUnidad", () => {
  it("escribe el precio con su unidad", () => {
    expect(precioConUnidad(12.15, "kg")).toBe("$12,15 por kg");
    expect(precioConUnidad(1.5, "l")).toBe("$1,50 por litro");
    expect(precioConUnidad(0.3, "unidad")).toBe("$0,30 por unidad");
  });
});

describe("nivelMargen", () => {
  it("verde >= 60, ámbar 30-60, rojo < 30", () => {
    expect([75, 60, 59.9, 30, 29.9, 0, -5].map(nivelMargen)).toEqual(["ok", "ok", "warn", "warn", "bad", "bad", "bad"]);
  });
});

describe("cambioPrecio", () => {
  it("subir es rojo con flecha arriba y signo +", () => {
    expect(cambioPrecio(18)).toEqual({ flecha: "↑", texto: "+18 %", nivel: "bad" });
  });
  it("bajar es verde con flecha abajo y signo -", () => {
    expect(cambioPrecio(-5.5)).toEqual({ flecha: "↓", texto: "-5,5 %", nivel: "ok" });
  });
  it("sin cambio no lleva color", () => {
    expect(cambioPrecio(0)).toEqual({ flecha: "=", texto: "± 0 %", nivel: null });
    expect(cambioPrecio(0.04)?.nivel).toBeNull();
  });
  it("sin precio anterior no hay cambio", () => {
    expect(cambioPrecio(null)).toBeNull();
  });
});
