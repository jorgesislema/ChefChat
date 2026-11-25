import { describe, expect, it } from "vitest";
import { etiquetaDias } from "./format";
import { avisoDiferencia, leerTope, pestanaMenu, queryDeSugerencia, textoStock } from "./menu";

describe("etiquetaDias (vencimiento)", () => {
  it("mañana y en N días", () => {
    expect(etiquetaDias(1)).toBe("Vence mañana");
    expect(etiquetaDias(3)).toBe("Vence en 3 días");
  });
});

describe("avisoDiferencia", () => {
  it("no avisa hasta 30 % ni sin dato", () => {
    expect(avisoDiferencia(30)).toBeNull();
    expect(avisoDiferencia(-30)).toBeNull();
    expect(avisoDiferencia(null)).toBeNull();
  });
  it("avisa más caro o más barato", () => {
    expect(avisoDiferencia(45.4)).toContain("45 % más caro");
    expect(avisoDiferencia(-52)).toContain("52 % más barato");
  });
});

describe("queryDeSugerencia", () => {
  it("incluye sin y tope", () => {
    const q = queryDeSugerencia({ comidas: ["desayuno", "almuerzo"], tope: 12.5, sin: ["gluten", "lacteos"], dias: 3, por_vencer: true, semilla: 2 });
    expect(q).toBe("comidas=desayuno,almuerzo&tope=12.5&sin=gluten,lacteos&dias=3&por_vencer=true&semilla=2");
  });
  it("omite tope y sin vacíos", () => {
    const q = queryDeSugerencia({ comidas: ["cena"], tope: null, sin: [], dias: 1, por_vencer: false, semilla: 0 });
    expect(q).toBe("comidas=cena&dias=1&por_vencer=false&semilla=0");
  });
});

describe("leerTope", () => {
  it("acepta coma, rechaza vacío y negativos", () => {
    expect(leerTope("12,5")).toBe(12.5);
    expect(leerTope("")).toBeNull();
    expect(leerTope("-3")).toBeNull();
    expect(leerTope("abc")).toBeNull();
  });
});

describe("pestanaMenu y textoStock", () => {
  it("pestaña desconocida cae en cocinar", () => {
    expect(pestanaMenu("armar")).toBe("armar");
    expect(pestanaMenu("x")).toBe("cocinar");
    expect(pestanaMenu(null)).toBe("cocinar");
  });
  it("texto de stock", () => {
    expect(textoStock({ kg: 2.5 })).toBe("2,5 kg");
  });
});
