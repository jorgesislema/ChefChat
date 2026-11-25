import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreguntaExamen } from "./PreguntaExamen";

const pregunta = {
  id: 7, enunciado: "¿Cuánto dura el lavado de manos?",
  opciones: [{ i: 2, texto: "5 segundos" }, { i: 0, texto: "20 segundos" }, { i: 3, texto: "1 segundo" }, { i: 1, texto: "No hace falta" }],
};

describe("PreguntaExamen", () => {
  it("muestra enunciado y 4 opciones", () => {
    render(<PreguntaExamen pregunta={pregunta} onElegir={() => {}} />);
    expect(screen.getByText(pregunta.enunciado)).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(4);
  });
  it.each([["1", 2], ["2", 0], ["3", 3], ["4", 1]])("la tecla %s elige la opción con índice %i", async (tecla, i) => {
    const fn = vi.fn();
    render(<PreguntaExamen pregunta={pregunta} onElegir={fn} />);
    await userEvent.keyboard(tecla);
    expect(fn).toHaveBeenCalledWith(i);
  });
  it("ignora teclas 5 y cuando está deshabilitada", async () => {
    const fn = vi.fn();
    const { rerender } = render(<PreguntaExamen pregunta={pregunta} onElegir={fn} />);
    await userEvent.keyboard("5");
    rerender(<PreguntaExamen pregunta={pregunta} onElegir={fn} deshabilitada />);
    await userEvent.keyboard("1");
    expect(fn).not.toHaveBeenCalled();
  });
  it("clic elige la opción", async () => {
    const fn = vi.fn();
    render(<PreguntaExamen pregunta={pregunta} onElegir={fn} />);
    await userEvent.click(screen.getByText("20 segundos"));
    expect(fn).toHaveBeenCalledWith(0);
  });
});
