import { useSearchParams } from "react-router-dom";
import { HojaConteo } from "./HojaConteo";
import { ListaConteos } from "./ListaConteos";

/** Pestaña «Conteo»: la lista de conteos, o la hoja de uno si la dirección trae ?conteo=ID. */
export function Conteo() {
  const [sp, setSp] = useSearchParams();
  const id = Number(sp.get("conteo")) || null;
  return id
    ? <HojaConteo id={id} alVolver={() => setSp({ vista: "conteo" })} />
    : <ListaConteos alAbrir={(i) => setSp({ vista: "conteo", conteo: String(i) })} />;
}
