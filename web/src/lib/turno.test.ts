import { describe, expect, it } from "vitest";
import type { InformeTurno } from "./api";
import {
  calcularTotales, cuerpoGuardar, entero, formDesdeInforme, hace, hayCambios, nombreTurno, turnoDeAhora, validarInforme,
  type FilaForm, type FormInforme,
} from "./turno";

const fila = (o: Partial<FilaForm> = {}): FilaForm => ({
  clave: 1, receta_id: "R1", plato: "Arroz", servicio: "almuerzo", producido: "10", vendido: "7", costo_plato: 2, recibido: "", ...o,
});
const form = (o: Partial<FormInforme> = {}): FormInforme => ({
  chefId: "E1", personal: ["E1", "E2"], filas: [fila()], incidencias: [], observaciones: "", ...o,
});
const datos = { merma_total: 5.5, recuperado_total: 1.25, compras_total: 40 };

const informe: InformeTurno = {
  fecha: "2026-03-10", turno: "matutino", nombre_turno: "Mañana", servicios: ["desayuno", "almuerzo"], id: null, estado: "nuevo",
  chef_id: null, personal: ["E1"], producido: [{ receta_id: "R1", plato: "Arroz", servicio: "almuerzo", producido: 10, vendido: 7, costo_plato: 2 }],
  producido_editado: false, incidencias: [], observaciones: "", firmado_por: null, firmado_en: null,
  datos: {} as InformeTurno["datos"], totales: {} as InformeTurno["totales"], chefs: [], tipos_incidencia: ["otro"],
};

describe("calcularTotales", () => {
  it("suma platos y calcula el costo del sobrante", () => {
    const t = calcularTotales([fila(), fila({ producido: "4", vendido: "4" })], datos);
    expect(t).toMatchObject({ platos_producidos: 14, platos_vendidos: 11, platos_sobrantes: 3, costo_sobrante: 6, merma: 5.5, recuperado: 1.25, compras: 40 });
  });
  it("las filas sin costo suman sobrante pero no costo", () => {
    const t = calcularTotales([fila({ costo_plato: null })], datos);
    expect(t.platos_sobrantes).toBe(3);
    expect(t.costo_sobrante).toBe(0);
  });
  it("ignora números inválidos mientras se escribe", () => {
    const t = calcularTotales([fila({ producido: "", vendido: "abc" })], datos);
    expect(t.platos_producidos).toBe(0);
    expect(t.platos_sobrantes).toBe(0);
  });
  it("redondea el costo a centavos", () => {
    expect(calcularTotales([fila({ producido: "3", vendido: "0", costo_plato: 0.333 })], datos).costo_sobrante).toBe(1);
  });
});

describe("entero", () => {
  it("solo acepta enteros de 0 en adelante", () => {
    expect(entero(" 12 ")).toBe(12);
    expect(entero("0")).toBe(0);
    for (const malo of ["", "-1", "2.5", "2,5", "uno"]) expect(entero(malo)).toBeNaN();
  });
});

describe("validarInforme", () => {
  it("acepta un formulario correcto, sin chef ni personal para borrador", () => {
    expect(validarInforme(form(), true)).toEqual([]);
    expect(validarInforme(form({ chefId: "", personal: [] }), false)).toEqual([]);
  });
  it("rechaza vendido mayor que producido", () => {
    expect(validarInforme(form({ filas: [fila({ vendido: "11" })] }), false)[0]).toContain("no puedes vender más");
  });
  it("rechaza negativos y decimales", () => {
    const m = validarInforme(form({ filas: [fila({ producido: "-3", vendido: "1.5" })] }), false);
    expect(m).toHaveLength(2);
  });
  it("rechaza plato sin nombre e incidencia vacía", () => {
    const m = validarInforme(form({ filas: [fila({ plato: " " })], incidencias: [{ tipo: "otro", descripcion: "  " }] }), false);
    expect(m.some((x) => x.includes("nombre de plato"))).toBe(true);
    expect(m.some((x) => x.includes("incidencia 1"))).toBe(true);
  });
  it("para firmar exige chef y personal", () => {
    const m = validarInforme(form({ chefId: "", personal: [] }), true);
    expect(m).toEqual(["Elige el chef del turno.", "Marca al menos una persona que trabajó en el turno."]);
  });
  it("limita las observaciones a 1000 letras", () => {
    expect(validarInforme(form({ observaciones: "a".repeat(1001) }), false)).toHaveLength(1);
  });
});

describe("cuerpoGuardar", () => {
  it("convierte a números, recorta textos y no manda costo_plato", () => {
    const c = cuerpoGuardar("2026-03-10", "matutino", form({ filas: [fila({ plato: " Arroz " })], incidencias: [{ tipo: "otro", descripcion: " Falló el horno " }] }));
    expect(c.producido).toEqual([{ receta_id: "R1", plato: "Arroz", servicio: "almuerzo", producido: 10, vendido: 7, recibido: null }]);
    expect(JSON.stringify(c)).not.toContain("costo_plato");
    expect(c.incidencias).toEqual([{ tipo: "otro", descripcion: "Falló el horno" }]);
    expect(c.chef_id).toBe("E1");
  });
  it("manda producido null si no se tocó lo propuesto, y chef null si no hay", () => {
    const c = cuerpoGuardar("2026-03-10", "matutino", form({ chefId: "" }), true);
    expect(c.producido).toBeNull();
    expect(c.chef_id).toBeNull();
  });
});

describe("hayCambios", () => {
  it("no detecta cambios en un formulario recién cargado", () => {
    expect(hayCambios(formDesdeInforme(informe), formDesdeInforme(informe))).toBe(false);
  });
  it("ignora el orden del personal y los espacios sobrantes", () => {
    const a = form(), b = form({ personal: ["E2", "E1"], filas: [fila({ plato: "Arroz ", clave: 9 })] });
    expect(hayCambios(b, a)).toBe(false);
  });
  it("detecta cambios en números, personal, incidencias y observaciones", () => {
    const base = form();
    expect(hayCambios(form({ filas: [fila({ vendido: "6" })] }), base)).toBe(true);
    expect(hayCambios(form({ personal: ["E1"] }), base)).toBe(true);
    expect(hayCambios(form({ incidencias: [{ tipo: "otro", descripcion: "x" }] }), base)).toBe(true);
    expect(hayCambios(form({ observaciones: "hola" }), base)).toBe(true);
  });
});

describe("turnos y fechas", () => {
  it("nombra los turnos", () => {
    expect(nombreTurno("matutino")).toBe("Mañana");
    expect(nombreTurno("vespertino")).toBe("Tarde");
    expect(nombreTurno("nocturno")).toBe("Noche");
  });
  it("propone el turno según la hora", () => {
    expect(turnoDeAhora(new Date(2026, 2, 10, 8))).toBe("matutino");
    expect(turnoDeAhora(new Date(2026, 2, 10, 15))).toBe("vespertino");
    expect(turnoDeAhora(new Date(2026, 2, 10, 21))).toBe("nocturno");
  });
  it("calcula fechas pasadas", () => {
    expect(hace(7, new Date(2026, 2, 10))).toBe("2026-03-03");
    expect(hace(30, new Date(2026, 2, 10))).toBe("2026-02-08");
  });
});

describe("recibido (lo cuenta otra persona)", () => {
  it("vacío se manda como null y un número como entero", () => {
    const c = cuerpoGuardar("2026-03-10", "matutino", form({ filas: [fila(), fila({ clave: 2, recibido: " 9 " })] }));
    expect(c.producido?.map((p) => p.recibido)).toEqual([null, 9]);
  });
  it("se lee del servidor: null queda vacío", () => {
    expect(formDesdeInforme(informe).filas[0].recibido).toBe("");
    const conRecibido = { ...informe, producido: [{ ...informe.producido[0], recibido: 8 }] };
    expect(formDesdeInforme(conRecibido).filas[0].recibido).toBe("8");
  });
  it("no puede pasar lo producido ni ser texto", () => {
    expect(validarInforme(form({ filas: [fila({ recibido: "11" })] }), false).join(" ")).toMatch(/recibir más de lo que se produjo/);
    expect(validarInforme(form({ filas: [fila({ recibido: "abc" })] }), false).join(" ")).toMatch(/recibido debe ser un número/);
    expect(validarInforme(form({ filas: [fila({ recibido: "10" })] }), false)).toEqual([]);
  });
  it("cambiar lo recibido cuenta como cambio sin guardar", () => {
    const a = form({ filas: [fila()] });
    expect(hayCambios({ ...a, filas: [fila({ recibido: "5" })] }, a)).toBe(true);
  });
});
