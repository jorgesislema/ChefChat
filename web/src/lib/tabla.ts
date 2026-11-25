const FILA = /^\s*[-*•]\s+(.+\|.+)$/;

const limpiar = (c: string, prefijo: RegExp) => c.trim().replace(prefijo, "").replace(/\|/g, "/");

/**
 * Convierte bloques de líneas "- A | lote B | C kg | vence D" en una tabla markdown
 * (Producto, Lote, Cantidad, Vence). Lo demás queda igual.
 */
export function listaATabla(texto: string): string {
  const lineas = texto.split("\n");
  const salida: string[] = [];
  let i = 0;
  while (i < lineas.length) {
    const filas: string[][] = [];
    let j = i;
    while (j < lineas.length) {
      const m = FILA.exec(lineas[j]);
      const cols = m?.[1].split("|");
      if (!cols || cols.length !== 4) break;
      filas.push([
        limpiar(cols[0], /^$/),
        limpiar(cols[1], /^lote\s+/i),
        limpiar(cols[2], /^$/),
        limpiar(cols[3], /^vence\s+/i),
      ]);
      j++;
    }
    if (filas.length) {
      if (salida.length && salida[salida.length - 1].trim() !== "") salida.push("");
      salida.push("| Producto | Lote | Cantidad | Vence |", "|---|---|---|---|");
      filas.forEach((f) => salida.push(`| ${f.join(" | ")} |`));
      salida.push("");
      i = j;
    } else {
      salida.push(lineas[i]);
      i++;
    }
  }
  return salida.join("\n");
}
