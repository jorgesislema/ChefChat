import { queryDeSugerencia } from "./menu";

export const MSG_SIN_CONEXION = "No puedo conectar con ChefChat. Revisa que el programa esté abierto.";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError(MSG_SIN_CONEXION);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* cuerpo no JSON */
    }
    if (res.status === 400 && detail) throw new ApiError(detail, 400);
    throw new ApiError("Algo salió mal. Intenta de nuevo en un momento.", res.status);
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError("Algo salió mal. Intenta de nuevo en un momento.", res.status);
  }
}

const post = <T>(url: string, body?: unknown) =>
  request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

const put = <T>(url: string, body: unknown) =>
  request<T>(url, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const del = <T>(url: string) => request<T>(url, { method: "DELETE" });

const upload = <T>(url: string, archivo: File) => {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo);
  return request<T>(url, { method: "POST", body: cuerpo });
};

// ---- tipos de cada respuesta ----
export type TipoProducto = "alimento" | "limpieza";
export interface Lote {
  producto: string;
  categoria: string | null;
  tipo?: TipoProducto;
  lote: string;
  cantidad: number;
  unidad: string;
  vence: string;
}
export interface MermaMotivo { motivo: string; costo: number; veces: number }
export interface Persona { estado: string; n: number }
export interface FilaReporte {
  id_empleado: string; nombre: string; tema: string; intentos: number; mejor_nota: number; aprobado: number | null;
}
export interface PreguntaFallada { enunciado: string; documento: string; seccion: string; fallos: number }
export interface Reporte { por_persona: FilaReporte[]; mas_falladas: PreguntaFallada[] }
export interface Resumen {
  fecha: string;
  vencen_7_dias: { lotes: number; items: Lote[] };
  vencen_diciembre: { lotes: number };
  ya_vencidos: { lotes: number };
  mermas_por_motivo: MermaMotivo[];
  mermas_total: number;
  personal: Persona[];
  examenes: Reporte;
}
export interface ProductoStock { producto: string; categoria: string | null; tipo?: TipoProducto; stock: number; unidad: string }
export interface Merma {
  fecha: string; producto: string; cantidad: number; unidad: string; motivo: string; costo_estimado: number | null;
}
export interface Trabajador { id_empleado: string; nombre_completo: string; cargo: string | null; turno: string | null }
export interface Tema { tema: string; aprobadas: number | null; pendientes: number | null }
export interface OpcionPublica { i: number; texto: string }
export interface PreguntaPublica { id: number; enunciado: string; opciones: OpcionPublica[] }
export interface Intento {
  intento_id: number; modo: "practica" | "evaluacion"; minutos: number | null; preguntas: PreguntaPublica[];
}
export type RespuestaExamen =
  | { correcta: boolean; respuesta_correcta: number; explicacion: string; fuente: string }
  | { guardada: true };
export interface Fallada { pregunta: string; fuente: string; explicacion: string; respuesta_correcta: string }
export interface Resultado {
  nota: number; aprobado: boolean | null; aciertos: number; total: number; nota_minima: number;
  fuera_de_tiempo: boolean; falladas: Fallada[];
}
export type EstadoPregunta = "pendiente" | "revisar" | "aprobada" | "retirada";
export interface PreguntaBanco {
  id: number; tema: string; enunciado: string; opciones: string[]; correcta: number; explicacion: string | null;
  documento: string | null; seccion: string | null; puntaje_jev: number | null; estado: EstadoPregunta;
}
export interface Edicion { enunciado?: string; opciones?: string[]; correcta?: number; explicacion?: string }
export interface ManualResumen { id: number; nombre: string; tipo: string; letras: number }
export interface Manual { id: number; nombre: string; texto: string }
export interface CargaRecetas { archivo: string; nuevas: number; actualizadas: number; n_rechazadas: number; rechazadas: { fila: number; motivo: string }[] }
export interface CargaManual { archivo: string; caracteres: number; reemplazo: boolean; manuales: number; fragmentos: number }
export interface ChatRespuesta { respuesta: string; error?: boolean }

export type UnidadPrecio = "kg" | "l" | "unidad";
export interface Proveedor {
  id: number; nombre: string; contacto: string | null; telefono: string | null; dias_entrega: string | null;
  notas: string | null; es_demo: number; n_productos?: number;
}
export interface ProductoProveedor {
  producto_id: number; producto: string; categoria: string | null; tipo: TipoProducto; precio: number;
  unidad_precio: UnidadPrecio; fecha: string; precio_anterior: number | null; cambio_pct: number | null;
  es_mas_barato: boolean; mejor_precio: number | null; mejor_proveedor: string | null;
}
export interface NuevoProveedor { nombre: string; contacto?: string; telefono?: string; dias_entrega?: string; notas?: string }
export interface NuevoPrecio { producto: string; precio: number; unidad_precio: UnidadPrecio; categoria?: string }
export interface AlertaPrecio {
  producto: string; proveedor: string; anterior: number; actual: number; unidad_precio: UnidadPrecio; cambio_pct: number; fecha: string;
}
export interface ProductoCatalogo { id: number; nombre: string; categoria: string | null; tipo: TipoProducto }
export interface RecetaResumen {
  id_receta: string; nombre: string; categoria: string | null; tiempo_prep: string | number | null; alergenos: string | null;
  costo_archivo: number | null; costo_calculado: number | null; cobertura: number; porciones: number | null;
  costo_porcion: number | null; precio_venta: number | null;
  costo_plato: number | null; fuente_costo: "archivo" | "calculado";
}
export interface IngredienteReceta {
  ingrediente: string; producto: string | null; cantidad: number | null; unidad: string | null; costo: number | null;
  nota: string | null; precio: number | null; unidad_precio: UnidadPrecio | null; proveedor: string | null;
}
export interface RecetaDetalle extends Omit<RecetaResumen, "porciones"> {
  instrucciones: string | null; porciones_supuestas: boolean; porciones_usadas: number; margen_pct: number | null;
  ingredientes: IngredienteReceta[]; diferencia_pct: number | null;
}

export type Comida = "desayuno" | "almuerzo" | "merienda" | "cena";
export interface CostoComida { minimo: number; tipico: number; maximo: number; platos: string[] }
export interface MenuCostos { por_comida: Record<Comida, CostoComida | null>; nota: string }
export interface PlatoSugerido {
  id_receta: string; nombre: string; categoria: string | null; costo_plato: number | null; fuente_costo: string;
  alergenos: string[]; usa_por_vencer: string[];
}
export interface ComidaSugerida {
  servicio: Comida; platos: PlatoSugerido[]; costo_persona: number | null; tope: number | null;
  cumple_tope: boolean; nota: string | null;
}
export interface DiaSugerido { fecha: string; costo_persona: number | null; comidas: ComidaSugerida[] }
export interface MenuSugerencia {
  dias: DiaSugerido[]; tope_dia: number | null; excluye: string[]; usa_por_vencer: boolean;
  costo_promedio_dia: number | null; cumple_tope: boolean; aviso: string | null;
}
export interface ParamsSugerencia {
  comidas: string[]; tope?: number | null; sin: string[]; dias: number; por_vencer: boolean; semilla: number;
}
export type StockPorUnidad = Partial<Record<UnidadPrecio, number>>;
export interface PorVencer { producto_id: number; producto: string; vence: string; dias: number; stock: StockPorUnidad }
export interface UsoProducto {
  producto: string; vence: string; dias: number; stock: number; unidad: string; necesita_por_plato: number; alcanza_para: number;
}
export interface RecetaCocinar {
  id_receta: string; nombre: string; categoria: string | null; costo_plato: number | null; alergenos: string[];
  porciones_posibles: number; usa: UsoProducto[];
}
export interface MenuCocinar { hoy: string; dias: number; por_vencer: PorVencer[]; recetas: RecetaCocinar[]; aviso: string | null }
export interface Sobrante {
  id: number; producto: string; cantidad: number; unidad: string; registrado: string; usar_hasta: string; vigente: boolean;
  recetas: { id_receta: string; nombre: string; costo_plato: number | null }[]; mensaje: string | null;
}
export interface MenuAlergenos { alergenos: string[]; comidas: string[] }

// ---- edicion de inventario, productos y proveedores ----
export interface LoteInv {
  id: number; producto_id: number; producto: string; categoria: string | null; tipo: TipoProducto; lote: string | null;
  cantidad: number; unidad: string; fecha_ingreso: string; fecha_caducidad_fija: string | null; vence: string;
}
export interface NuevoLote {
  producto: string; cantidad: number; unidad: string; fecha_ingreso?: string; fecha_caducidad?: string; id_lote?: string; categoria?: string;
}
export interface EditaLote { cantidad?: number; unidad?: string; fecha_ingreso?: string; fecha_caducidad?: string; quitar_caducidad?: boolean }
export interface ProductoCat {
  id: number; nombre: string; categoria: string | null; tipo: TipoProducto; vida_util_dias: number | null; origen: string | null;
  stock: number; unidad_stock: string | null; n_proveedores: number;
  mejor_precio: number | null; mejor_unidad: string | null; mejor_proveedor: string | null;
  /** peso de 1 unidad (huevo, pieza) o de 1 litro, en kg; null = sin dato (las unidades no suman en el balance) */
  kg_por_unidad: number | null;
}
export interface EditaProducto { nombre?: string; categoria?: string; tipo?: TipoProducto; vida_util_dias?: number }
export interface EditaProveedor { nombre?: string; contacto?: string; telefono?: string; dias_entrega?: string; notas?: string }
export interface PrecioProveedor {
  proveedor_id: number; proveedor: string; precio: number; unidad_precio: "kg" | "l" | "unidad"; fecha: string; cambio_pct: number | null;
}
export interface Cambio { id: number; fecha: string; entidad: string; accion: string; detalle: string }
export interface Ok { ok: boolean }

// ---- analisis del dueno ----
export interface PeriodoDatos { desde: string | null; hasta: string | null }
export interface MermaMes { mes: string; texto: string; costo: number; registros: number; dias_con_datos: number }
export interface AnalisisMermas {
  periodo: PeriodoDatos; total: number; registros: number; por_mes: MermaMes[];
  por_motivo: { motivo: string; costo: number; veces: number; pct: number | null }[];
  por_producto: { producto: string; costo: number; veces: number; pct: number | null }[]; mensajes: string[];
}
export interface AnalisisRecuperacion {
  recuperado: number; perdido: number; reutilizados: number; desperdiciados: number; donados: number; guardados: number;
  kg_reutilizados: number; kg_desperdiciados: number; pct_recuperado: number | null; mensajes: string[];
}
export interface PlatoProd {
  plato: string; receta_id: string | null; producido: number; vendido: number; costo_plato: number | null;
  sobrante: number; pct_sobrante: number | null; costo_sobrante: number | null;
}
export interface AnalisisProduccion {
  periodo: PeriodoDatos; demo: boolean; producido: number; vendido: number; sobrante: number; pct_sobrante: number | null;
  costo_sobrante: number; por_plato: PlatoProd[];
  por_servicio: { servicio: string; producido: number; vendido: number; pct_sobrante: number | null }[]; mensajes: string[];
}
export interface PlatoRent {
  plato: string; receta_id: string | null; vendido: number; ingresos: number; costo: number; ganancia: number; margen_pct: number | null;
}
export interface AnalisisRentables {
  periodo: PeriodoDatos; demo: boolean; ingresos: number; ganancia: number; mas_ganan: PlatoRent[]; menos_ganan: PlatoRent[];
  sin_costo: string[]; mensajes: string[];
}
export interface Analisis {
  mermas: AnalisisMermas; recuperacion: AnalisisRecuperacion; produccion: AnalisisProduccion; rentables: AnalisisRentables; costo_real: CostoReal;
}
export type DestinoSobrante = "reutilizado" | "desperdicio" | "donacion";

// ---- compras y costo real ----
export interface Compra {
  id: number; fecha: string; proveedor_id: number; proveedor: string; producto_id: number; producto: string; categoria: string | null;
  tipo: TipoProducto; cantidad: number; unidad: string; precio: number; unidad_precio: UnidadPrecio; total: number;
  factura: string | null; notas: string | null; es_demo: number; sumo_lote: number;
}
export interface ListaCompras {
  compras: Compra[]; n: number; total: number; total_alimentos: number; total_limpieza: number;
  por_proveedor: { proveedor: string; total: number }[]; demo: boolean;
}
export interface NuevaCompra {
  proveedor_id: number; producto: string; cantidad: number; unidad: string; precio: number; unidad_precio: UnidadPrecio;
  fecha?: string; vence?: string; factura?: string; notas?: string; crear_lote?: boolean; actualizar_precio?: boolean; categoria?: string;
}
export interface CostoReal {
  periodo: { desde: string | null; hasta: string | null; dias_con_ventas: number; dias_con_compras: number };
  demo: boolean; ingresos: number; teorico: number; teorico_producido: number; real: number; merma_registrada: number;
  teorico_pct: number | null; real_pct: number | null; objetivo_pct: number; diferencia: number; diferencia_pct: number | null;
  desglose: { vendido: number; sobreproduccion: number; merma_registrada: number; sin_explicar: number } | null;
  /** "conteo" = exacto (inventario inicial + compras - inventario final); "compras" = aproximado (solo compras) */
  metodo: "conteo" | "compras"; comprado: number;
  inventario_inicial: { id: number; fecha: string; valor: number } | null; inventario_final: { id: number; fecha: string; valor: number } | null;
  platos_sin_costo: number; mensajes: string[];
}

// ---- conteo de inventario ----
export interface ConteoResumen {
  id: number; fecha: string; estado: "abierto" | "cerrado"; incluye_limpieza: number; notas: string | null;
  cerrado_por: string | null; cerrado_en: string | null; ajusto_inventario: number; valor_sistema: number | null; valor_contado: number | null;
  es_demo: number; n_lineas: number; n_contadas: number;
}
export interface LineaConteo {
  id: number; conteo_id: number; producto_id: number; producto: string; categoria: string | null; tipo: TipoProducto;
  unidad: UnidadPrecio; cantidad_sistema: number; cantidad_contada: number | null; precio: number | null;
  valor_sistema: number | null; valor_contado: number | null; diferencia: number | null; diferencia_pct: number | null; valor_diferencia: number | null;
}
export interface ConteoDetalle extends Omit<ConteoResumen, "n_lineas" | "n_contadas"> {
  lineas: LineaConteo[]; n_lineas: number; n_contadas: number; valor_sistema_actual: number; valor_contado_actual: number;
  n_alertas: number; mensajes: string[];
}

// ---- informe del turno ----
export type Turno = "matutino" | "vespertino" | "nocturno";
export interface PersonaTurno { id_empleado: string; nombre: string; cargo: string | null }
export interface PlatoTurno {
  receta_id: string | null; plato: string; servicio: string | null; producido: number; vendido: number; costo_plato: number | null;
  /** unidades que contó OTRA persona (mostrador, despacho); null = no se contó */
  recibido?: number | null;
}
export interface IncidenciaTurno { tipo: string; descripcion: string }
export interface DatosTurno {
  producido: PlatoTurno[];
  mermas: { producto: string; cantidad: number; unidad: string; motivo: string; costo_estimado: number | null }[];
  merma_total: number; nota_merma: string | null;
  recuperado: { producto: string; cantidad: number; unidad: string; valor: number | null }[]; recuperado_total: number;
  sobrantes_nuevos: { producto: string; cantidad: number; unidad: string; destino: string }[];
  compras: { proveedor: string; producto: string; cantidad: number; unidad: string; total: number }[]; compras_total: number;
  incidencias_registradas: { tipo: string; descripcion: string; hora: string }[];
  personal: { trabajan: PersonaTurno[]; descansan: PersonaTurno[]; ausentes: (PersonaTurno & { motivo: string; hasta: string })[] };
  /** balance de masas del turno (congelado al firmar) */
  balance?: Balance;
}

// ---- balance del turno (kilos y unidades) ----
/** alarma = pasa la tolerancia; cerca = más del 75 % de la tolerancia; sin_entregas = bodega no anotó nada */
export type EstadoBalance = "bien" | "cerca" | "alarma" | "sin_entregas" | "sin_datos";
export type TipoSalida = "comida_personal" | "residuo_limpieza" | "muestra" | "otro";
export interface KgBalance {
  entregado: number; devuelto: number; entro: number; salio_bueno: number; perdida_normal: number; merma: number;
  comida_personal: number; residuo_limpieza: number; muestra: number; otro: number; anotado: number;
  /** entró − explicado. POSITIVO = FALTA (se perdió sin anotar); negativo = sobra */
  sin_explicar: number;
}
export interface LineaIngrediente {
  producto_id: number; producto: string; entregado: number; devuelto: number; neto: number; uso_receta: number; merma: number;
  /** positivo = falta de este ingrediente */
  diferencia: number; diferencia_pct: number | null; valor_diferencia: number | null;
  calculable: boolean; sin_entrega: boolean;
}
export interface PlatoBalance {
  receta_id: string | null; plato: string | null; producido: number; vendido: number; recibido: number | null; perdidas_unidades: number | null;
  kg_bueno: number; kg_perdida_normal: number; origen_peso: "peso por unidad" | "peso de la receta";
  perdida_normal_pct: number; tolerancia_pct: number; estandar_por_defecto: boolean; faltan_pesos: boolean;
}
export interface MovimientoBalance {
  id: number; tipo: "entrega" | "devolucion"; producto: string | null; cantidad: number; unidad: string;
  entrego: string | null; recibio: string | null; es_demo: number;
}
export interface SalidaBalance { id: number; tipo: TipoSalida; nombre_tipo: string; kg: number; producto: string | null; nota: string | null; persona: string | null }
export interface MermaBalance { id: number; producto: string; cantidad: number; unidad: string; motivo: string; kg: number | null; costo: number | null }
export interface Balance {
  fecha: string; turno: Turno; estado: EstadoBalance; kg: KgBalance;
  sin_explicar_pct: number | null; tolerancia_pct: number; costo_kg: number | null;
  /** positivo = dinero perdido sin explicar */
  sin_explicar_dinero: number | null;
  por_ingrediente: LineaIngrediente[]; por_plato: PlatoBalance[];
  unidades: { producido: number; vendido: number; recibido: number | null; perdidas: number | null };
  movimientos: MovimientoBalance[]; salidas: SalidaBalance[]; mermas: MermaBalance[];
  mensajes: string[]; avisos: string[];
}
export interface FilaTendencia {
  fecha: string; turno: Turno; estado: EstadoBalance; entro_kg: number; sin_explicar_kg: number;
  sin_explicar_pct: number | null; tolerancia_pct: number; sin_explicar_dinero: number | null;
}
export interface TendenciaBalance {
  turnos: FilaTendencia[]; por_turno: { turno: Turno; turnos: number; promedio_pct: number; alarmas: number }[]; mensajes: string[];
}
export interface EstandarReceta {
  receta_id: string; peso_unidad_g: number | null; perdida_normal_pct: number; tolerancia_pct: number; notas: string | null; es_defecto: boolean;
}
export interface NuevoMovimiento {
  fecha: string; turno: Turno; tipo: "entrega" | "devolucion"; producto: string; cantidad: number; unidad: string;
  entrego?: string; recibio?: string; descontar_inventario?: boolean;
}
export interface NuevaSalida { fecha: string; turno: Turno; tipo: TipoSalida; kg: number; nota?: string; persona?: string; producto?: string | null }
export interface NuevaMermaTurno { fecha: string; turno: Turno; producto: string; cantidad: number; unidad: string; motivo: string; costo?: number | null }
export interface TotalesTurno {
  platos_producidos: number; platos_vendidos: number; platos_sobrantes: number; costo_sobrante: number; merma: number; recuperado: number; compras: number;
}
export interface InformeTurno {
  fecha: string; turno: Turno; nombre_turno: string; servicios: string[]; id: number | null; estado: "nuevo" | "borrador" | "firmado";
  chef_id: string | null; personal: string[]; producido: PlatoTurno[]; producido_editado: boolean; incidencias: IncidenciaTurno[];
  observaciones: string; firmado_por: string | null; firmado_en: string | null; datos: DatosTurno; totales: TotalesTurno;
  chefs: PersonaTurno[]; tipos_incidencia: string[];
}
export interface GuardaInforme {
  fecha: string; turno: Turno; chef_id?: string | null; personal: string[]; producido?: Omit<PlatoTurno, "costo_plato">[] | null;
  incidencias: IncidenciaTurno[]; observaciones: string;
}
export interface FilaInforme {
  id: number; fecha: string; turno: Turno; nombre_turno: string; chef: string | null; estado: "borrador" | "firmado";
  firmado_por: string | null; firmado_en: string | null; n_incidencias: number; totales: TotalesTurno | null;
}

export const api = {
  resumen: () => request<Resumen>("/api/resumen"),
  inventario: () => request<{ productos: ProductoStock[] }>("/api/inventario"),
  vencimientos: (p: { semanas?: number; mes?: number }) =>
    request<{ lotes: Lote[] }>(`/api/vencimientos?${p.mes ? `mes=${p.mes}` : `semanas=${p.semanas ?? 4}`}`),
  mermas: () => request<{ mermas: Merma[] }>("/api/mermas"),
  trabajadores: () => request<{ trabajadores: Trabajador[] }>("/api/trabajadores"),
  temas: () => request<{ temas: Tema[] }>("/api/examenes/temas"),
  iniciar: (b: { id_empleado: string; tema: string; modo: string; n?: number }) =>
    post<Intento>("/api/examenes/iniciar", b),
  responder: (id: number, b: { pregunta_id: number; elegida: number }) =>
    post<RespuestaExamen>(`/api/examenes/${id}/responder`, b),
  cerrar: (id: number) => post<Resultado>(`/api/examenes/${id}/cerrar`),
  reporte: () => request<Reporte>("/api/examenes/reporte"),
  preguntas: (estado: string) => request<{ preguntas: PreguntaBanco[] }>(`/api/examenes/preguntas?estado=${estado}`),
  cambiarEstado: (id: number, b: { estado: EstadoPregunta; editado?: Edicion }) =>
    post<{ ok: boolean }>(`/api/examenes/preguntas/${id}/estado`, b),
  manuales: () => request<{ manuales: ManualResumen[] }>("/api/manuales"),
  manual: (id: number) => request<Manual>(`/api/manuales/${id}`),
  proveedores: () => request<{ proveedores: Proveedor[] }>("/api/proveedores"),
  proveedor: (id: number) => request<{ proveedor: Proveedor; productos: ProductoProveedor[] }>(`/api/proveedores/${id}`),
  crearProveedor: (b: NuevoProveedor) => post<{ id: number }>("/api/proveedores", b),
  guardarPrecio: (id: number, b: NuevoPrecio) =>
    post<{ producto_id: number; producto_creado: boolean }>(`/api/proveedores/${id}/precios`, b),
  alertasPrecios: () => request<{ alertas: AlertaPrecio[]; umbral_pct: number }>("/api/precios/alertas"),
  catalogo: () => request<{ productos: ProductoCatalogo[] }>("/api/catalogo"),
  recetas: (p: { q?: string; categoria?: string }) =>
    request<{ recetas: RecetaResumen[]; categorias: string[] }>(
      `/api/recetas?${new URLSearchParams({ q: p.q ?? "", categoria: p.categoria ?? "" })}`),
  receta: (id: string) => request<RecetaDetalle>(`/api/recetas/${encodeURIComponent(id)}`),
  guardarPorciones: (id: string, porciones: number) =>
    put<{ ok: boolean }>(`/api/recetas/${encodeURIComponent(id)}/porciones`, { porciones }),
  menuCostos: () => request<MenuCostos>("/api/menu/costos"),
  menuSugerencia: (p: ParamsSugerencia) => request<MenuSugerencia>(`/api/menu/sugerencia?${queryDeSugerencia(p)}`),
  menuCocinar: (dias: number, sin: string[] = []) =>
    request<MenuCocinar>(`/api/menu/cocinar?${new URLSearchParams({ dias: String(dias), ...(sin.length ? { sin: sin.join(",") } : {}) })}`),
  menuSobrantes: () => request<{ sobrantes: Sobrante[] }>("/api/menu/sobrantes"),
  // inventario, productos y proveedores (editar)
  lotes: (p: { q?: string; tipo?: string } = {}) =>
    request<{ lotes: LoteInv[] }>(`/api/inventario/lotes?q=${encodeURIComponent(p.q ?? "")}&tipo=${p.tipo ?? ""}`),
  crearLote: (b: NuevoLote) => post<{ id: number; lote: string; producto_id: number; producto_creado: boolean }>("/api/inventario/lotes", b),
  editarLote: (id: number, b: EditaLote) => put<Ok>(`/api/inventario/lotes/${id}`, b),
  quitarLote: (id: number) => del<Ok>(`/api/inventario/lotes/${id}`),
  productosInv: (p: { q?: string; categoria?: string; tipo?: string } = {}) =>
    request<{ productos: ProductoCat[]; categorias: string[] }>(
      `/api/inventario/productos?q=${encodeURIComponent(p.q ?? "")}&categoria=${encodeURIComponent(p.categoria ?? "")}&tipo=${p.tipo ?? ""}`),
  editarProducto: (id: number, b: EditaProducto) => put<Ok>(`/api/inventario/productos/${id}`, b),
  quitarProducto: (id: number) => del<Ok>(`/api/inventario/productos/${id}`),
  pesoProducto: (id: number, kg_por_unidad: number | null) => put<Ok>(`/api/inventario/productos/${id}/peso`, { kg_por_unidad }),
  // balance del turno
  balance: (fecha: string, turno: Turno) =>
    request<Balance>(`/api/balance?fecha=${encodeURIComponent(fecha)}&turno=${encodeURIComponent(turno)}`),
  tendenciaBalance: (p: { desde?: string; hasta?: string } = {}) =>
    request<TendenciaBalance>(`/api/balance/tendencia?desde=${encodeURIComponent(p.desde ?? "")}&hasta=${encodeURIComponent(p.hasta ?? "")}`),
  anotarMovimiento: (b: NuevoMovimiento) => post<{ id: number; aviso: string | null }>("/api/balance/movimientos", b),
  quitarMovimiento: (id: number) => del<Ok>(`/api/balance/movimientos/${id}`),
  anotarSalida: (b: NuevaSalida) => post<{ id: number }>("/api/balance/salidas", b),
  quitarSalida: (id: number) => del<Ok>(`/api/balance/salidas/${id}`),
  anotarMermaTurno: (b: NuevaMermaTurno) => post<{ id: number; costo: number | null }>("/api/balance/mermas", b),
  estandar: (recetaId: string) => request<EstandarReceta>(`/api/recetas/${encodeURIComponent(recetaId)}/estandar`),
  guardarEstandar: (recetaId: string, b: { peso_unidad_g: number | null; perdida_normal_pct: number; tolerancia_pct: number; notas?: string }) =>
    put<Ok>(`/api/recetas/${encodeURIComponent(recetaId)}/estandar`, b),
  editarProveedor: (id: number, b: EditaProveedor) => put<Ok>(`/api/proveedores/${id}`, b),
  quitarProveedor: (id: number) => del<Ok>(`/api/proveedores/${id}`),
  quitarProductoDeProveedor: (proveedorId: number, productoId: number) =>
    del<Ok>(`/api/proveedores/${proveedorId}/productos/${productoId}`),
  preciosDeProducto: (id: number) =>
    request<{ precios: PrecioProveedor[]; stock: { cantidad: number; unidad: string } }>(`/api/inventario/productos/${id}/precios`),
  cambios: (limite = 50) => request<{ cambios: Cambio[] }>(`/api/cambios?limite=${limite}`),
  // analisis del dueno
  analisis: (p: { desde?: string; hasta?: string } = {}) =>
    request<Analisis>(`/api/analisis?desde=${p.desde ?? ""}&hasta=${p.hasta ?? ""}`),
  destinoSobrante: (id: number, b: { destino: DestinoSobrante; valor_estimado?: number }) => post<Ok>(`/api/sobrantes/${id}/destino`, b),
  // compras y costo real
  compras: (p: { desde?: string; hasta?: string; proveedor_id?: number } = {}) =>
    request<ListaCompras>(`/api/compras?desde=${p.desde ?? ""}&hasta=${p.hasta ?? ""}${p.proveedor_id ? `&proveedor_id=${p.proveedor_id}` : ""}`),
  crearCompra: (b: NuevaCompra) =>
    post<{ id: number; total: number; producto_id: number; lote: string | null; producto_creado: boolean }>("/api/compras", b),
  anularCompra: (id: number) => del<{ lote_quitado: boolean; aviso: string | null }>(`/api/compras/${id}`),
  costoReal: (p: { desde?: string; hasta?: string } = {}) => request<CostoReal>(`/api/analisis/costo-real?desde=${p.desde ?? ""}&hasta=${p.hasta ?? ""}`),
  // conteo de inventario
  conteos: () => request<{ conteos: ConteoResumen[] }>("/api/conteos"),
  crearConteo: (b: { fecha?: string; incluye_limpieza?: boolean; notas?: string } = {}) =>
    post<{ id: number; fecha: string; lineas: number }>("/api/conteos", b),
  conteo: (id: number) => request<ConteoDetalle>(`/api/conteos/${id}`),
  contar: (id: number, cantidades: { producto_id: number; cantidad: number | null }[]) =>
    put<{ guardadas: number }>(`/api/conteos/${id}/cantidades`, { cantidades }),
  agregarAlConteo: (id: number, b: { producto: string; cantidad: number; unidad: string }) =>
    post<{ producto_id: number; unidad: string }>(`/api/conteos/${id}/productos`, b),
  cerrarConteo: (id: number, b: { cerrado_por: string; ajustar_inventario: boolean; sin_contar_igual: boolean }) =>
    post<{ valor_sistema: number; valor_contado: number; diferencia: number; ajustes: number }>(`/api/conteos/${id}/cerrar`, b),
  anularConteo: (id: number) => del<Ok>(`/api/conteos/${id}`),
  // informe del turno
  informes: (p: { desde?: string; hasta?: string } = {}) =>
    request<{ informes: FilaInforme[] }>(`/api/turnos?desde=${p.desde ?? ""}&hasta=${p.hasta ?? ""}`),
  informe: (fecha: string, turno: Turno) => request<InformeTurno>(`/api/turnos/informe?fecha=${fecha}&turno=${turno}`),
  guardarInforme: (b: GuardaInforme) => put<{ id: number; estado: string }>("/api/turnos/informe", b),
  firmarInforme: (b: { fecha: string; turno: Turno; firmado_por: string }) =>
    post<{ id: number; estado: string; firmado_en: string }>("/api/turnos/informe/firmar", b),
  menuAlergenos: () => request<MenuAlergenos>("/api/menu/alergenos"),
  cargarRecetas: (f: File) => upload<CargaRecetas>("/api/recetas/cargar", f),
  cargarManual: (f: File) => upload<CargaManual>("/api/manuales/cargar", f),
  chat: (mensaje: string) => post<ChatRespuesta>("/api/chat", { mensaje }),
};
