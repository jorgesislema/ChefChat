import { Trash2 } from "lucide-react";
import type { Compra } from "../../lib/api";
import { dinero } from "../../lib/format";
import { precioConUnidad } from "../../lib/precios";
import { Badge, Button, Tabla, Td, Th } from "../ui/ui";

const cantidadTxt = (n: number) => new Intl.NumberFormat("es", { maximumFractionDigits: 3 }).format(n);
const fechaTxt = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");

export function TablaCompras({ compras, onAnular }: { compras: Compra[]; onAnular: (c: Compra) => void }) {
  return (
    <Tabla>
      <thead>
        <tr>
          <Th>Fecha</Th><Th>Proveedor</Th><Th>Producto</Th><Th className="text-right">Cantidad</Th><Th>Precio</Th>
          <Th className="text-right">Total</Th><Th>Factura</Th><Th>Sumó al inventario</Th><Th><span className="sr-only">Acciones</span></Th>
        </tr>
      </thead>
      <tbody>
        {compras.map((c) => (
          <tr key={c.id}>
            <Td className="whitespace-nowrap tabular-nums">{fechaTxt(c.fecha)}</Td>
            <Td>{c.proveedor}</Td>
            <Td className="font-medium">{c.producto}</Td>
            <Td className="whitespace-nowrap text-right tabular-nums">{cantidadTxt(c.cantidad)} {c.unidad}</Td>
            <Td className="whitespace-nowrap tabular-nums">{precioConUnidad(c.precio, c.unidad_precio)}</Td>
            <Td className="text-right font-medium tabular-nums">{dinero(c.total)}</Td>
            <Td>{c.factura ?? <span className="text-muted">-</span>}</Td>
            <Td>{c.sumo_lote ? <Badge nivel="ok">Sí</Badge> : <span className="text-muted">No</span>}</Td>
            <Td>
              <Button variante="peligro" onClick={() => onAnular(c)} aria-label={`Anular la compra de ${c.producto} del ${fechaTxt(c.fecha)}`}>
                <Trash2 size={14} aria-hidden /> Anular
              </Button>
            </Td>
          </tr>
        ))}
      </tbody>
    </Tabla>
  );
}
