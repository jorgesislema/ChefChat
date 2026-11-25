import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Printer } from "lucide-react";
import { api, type InformeTurno, type RecetaResumen, type Trabajador } from "../../lib/api";
import { Avisos } from "../edicion/comun";
import { Badge, Button } from "../ui/ui";
import { fechaHora, calcularTotales, cuerpoGuardar, formDesdeInforme, hayCambios, validarInforme, type FormInforme } from "../../lib/turno";
import { Totales } from "./Totales";
import { Personal } from "./Personal";
import { Producido } from "./Producido";
import { Balance } from "./Balance";
import { LoQuePaso } from "./LoQuePaso";
import { Incidencias } from "./Incidencias";
import { Imprimible } from "./Imprimible";
import { Firmar } from "./Firmar";

interface Props {
  inicial: InformeTurno;
  todos: Trabajador[];
  recetas: RecetaResumen[];
  alSucio: (sucio: boolean) => void;
}

export function Editor({ inicial, todos, recetas, alSucio }: Props) {
  const qc = useQueryClient();
  const [inf, setInf] = useState(inicial);
  const [original, setOriginal] = useState<FormInforme>(() => formDesdeInforme(inicial));
  const [form, setForm] = useState<FormInforme>(original);
  const [errores, setErrores] = useState<string[]>([]);
  const [aviso, setAviso] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [firmando, setFirmando] = useState(false);

  const soloLectura = inf.estado === "firmado";
  const sucio = !soloLectura && hayCambios(form, original);
  useEffect(() => { alSucio(sucio); }, [sucio, alSucio]);
  useEffect(() => () => alSucio(false), [alSucio]);

  const totales = useMemo(() => calcularTotales(form.filas, inf.datos), [form.filas, inf.datos]);

  const nombres = useMemo(() => {
    const m = new Map<string, string>();
    for (const t of todos) m.set(t.id_empleado, t.nombre_completo);
    const p = inf.datos.personal;
    for (const x of [...p.descansan, ...p.ausentes, ...inf.chefs, ...p.trabajan]) m.set(x.id_empleado, x.nombre);
    return m;
  }, [todos, inf]);
  const nombre = (id: string) => nombres.get(id) ?? id;

  const cambiar = (parte: Partial<FormInforme>) => { setForm((f) => ({ ...f, ...parte })); setAviso(null); };

  /** Guarda y vuelve a leer el informe. Lanza el error del servidor si falla. */
  const guardar = async (): Promise<void> => {
    const sinTocar = !inf.producido_editado && !hayCambios({ ...form, chefId: "", personal: [], incidencias: [], observaciones: "" },
      { ...original, chefId: "", personal: [], incidencias: [], observaciones: "" });
    await api.guardarInforme(cuerpoGuardar(inf.fecha, inf.turno, form, sinTocar));
    const nuevo = await api.informe(inf.fecha, inf.turno);
    const f = formDesdeInforme(nuevo);
    setInf(nuevo); setOriginal(f); setForm(f);
    void qc.invalidateQueries({ queryKey: ["informes"] });
    void qc.invalidateQueries({ queryKey: ["balance", inf.fecha, inf.turno] });
  };

  const alGuardar = async () => {
    if (guardando) return;
    const m = validarInforme(form, false);
    setErrores(m);
    if (m.length) return;
    setGuardando(true);
    try { await guardar(); setAviso("Borrador guardado."); }
    catch (e) { setErrores([e instanceof Error ? e.message : "No pude guardar el informe. Intenta de nuevo."]); }
    finally { setGuardando(false); }
  };

  const alPedirFirma = () => {
    const m = validarInforme(form, true);
    setErrores(m);
    if (m.length === 0) setFirmando(true);
  };

  const alFirmar = async (quien: string) => {
    if (inf.estado === "nuevo" || sucio) await guardar();
    await api.firmarInforme({ fecha: inf.fecha, turno: inf.turno, firmado_por: quien });
    const nuevo = await api.informe(inf.fecha, inf.turno);
    const f = formDesdeInforme(nuevo);
    setInf(nuevo); setOriginal(f); setForm(f);
    setAviso("Informe firmado y cerrado.");
    void qc.invalidateQueries({ queryKey: ["informes"] });
  };

  // misma consulta que usa <Balance />: se comparte en cache y sirve para el impreso
  const bq = useQuery({ queryKey: ["balance", inf.fecha, inf.turno], queryFn: () => api.balance(inf.fecha, inf.turno), enabled: !soloLectura });
  const balance = soloLectura ? inf.datos.balance : bq.data;

  const personalImpreso = form.personal.map(nombre);

  return (
    <>
      <div className="no-print space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          {inf.estado === "firmado" ? <Badge nivel="ok">Firmado por {inf.firmado_por} el {fechaHora(inf.firmado_en)}</Badge>
            : <Badge nivel="warn">{inf.estado === "borrador" ? "Borrador" : "Nuevo"}</Badge>}
          {sucio && <span className="text-sm text-warn">Tienes cambios sin guardar.</span>}
        </div>

        <Totales t={totales} />

        <Personal datos={inf.datos.personal} chefs={inf.chefs} todos={todos} personal={form.personal} chefId={form.chefId}
          soloLectura={soloLectura} nombre={nombre} alPersonal={(personal) => cambiar({ personal })} alChef={(chefId) => cambiar({ chefId })} />

        <Producido filas={form.filas} recetas={recetas} editado={inf.producido_editado} soloLectura={soloLectura}
          hayVentas={inicial.producido.length > 0} alCambiar={(filas) => cambiar({ filas })} />

        <Balance fecha={inf.fecha} turno={inf.turno} firmado={soloLectura} congelado={inf.datos.balance} />

        <LoQuePaso d={inf.datos} />

        <Incidencias incidencias={form.incidencias} tipos={inf.tipos_incidencia} observaciones={form.observaciones} soloLectura={soloLectura}
          alIncidencias={(incidencias) => cambiar({ incidencias })} alObservaciones={(observaciones) => cambiar({ observaciones })} />

        <Avisos mensajes={errores} />
        {aviso && <p role="status" className="rounded-xl border border-ok/40 bg-ok/10 p-3 text-sm text-ok">{aviso}</p>}

        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" onClick={() => window.print()}><Printer size={14} aria-hidden /> Imprimir informe</Button>
          {!soloLectura && (
            <>
              <Button type="button" onClick={() => void alGuardar()} disabled={guardando}>
                {guardando && <Loader2 size={14} className="animate-spin" aria-hidden />} Guardar borrador
              </Button>
              <Button type="button" variante="primario" onClick={alPedirFirma} disabled={guardando}>Firmar y cerrar</Button>
            </>
          )}
        </div>
      </div>

      <Imprimible inf={inf} form={form} totales={totales} nombreChef={form.chefId ? nombre(form.chefId) : ""} nombresPersonal={personalImpreso} balance={balance} />

      {firmando && <Firmar inicial={form.chefId ? nombre(form.chefId) : ""} alFirmar={alFirmar} alCerrar={() => setFirmando(false)} />}
    </>
  );
}
