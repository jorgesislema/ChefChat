import { NavLink, Outlet } from "react-router-dom";
import { BookOpenCheck, ChefHat, ClipboardCheck, ClipboardList, FileText, GraduationCap, Home, Moon, Package, ShoppingCart, Sun, Trash2, Truck, UtensilsCrossed } from "lucide-react";
import { AsistenteFlotante } from "./AsistenteFlotante";
import { Logo } from "./Logo";
import { cx } from "./ui/ui";
import { useTema } from "../hooks/useTema";

const ITEMS = [
  { to: "/", nombre: "Inicio", Icono: Home },
  { to: "/inventario", nombre: "Inventario", Icono: Package },
  { to: "/proveedores", nombre: "Proveedores", Icono: Truck },
  { to: "/compras", nombre: "Compras", Icono: ShoppingCart },
  { to: "/recetas", nombre: "Recetas", Icono: ChefHat },
  { to: "/menu", nombre: "Menú", Icono: UtensilsCrossed },
  { to: "/mermas", nombre: "Mermas", Icono: Trash2 },
  { to: "/turno", nombre: "Informe del turno", Icono: ClipboardCheck },
  { to: "/capacitacion", nombre: "Capacitación", Icono: GraduationCap },
  { to: "/manuales", nombre: "Manuales", Icono: FileText },
  { to: "/panel", nombre: "Panel del dueño", Icono: ClipboardList },
];

export function Layout() {
  const { oscuro, alternar } = useTema();
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="no-print flex shrink-0 flex-col border-b border-line bg-surface md:sticky md:top-0 md:h-screen md:w-60 md:border-b-0 md:border-r">
        <div className="flex items-center gap-3 px-4 py-4">
          <Logo />
          <span className="text-xl font-bold tracking-tight">Chef<span className="text-brand">Chat</span></span>
          <button onClick={alternar} aria-label={oscuro ? "Cambiar a tema claro" : "Cambiar a tema oscuro"} className="ml-auto rounded-lg p-2 text-muted hover:bg-line/50 hover:text-ink md:hidden">
            {oscuro ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
        <nav aria-label="Principal" className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-1 md:flex-col md:overflow-visible">
          {ITEMS.map(({ to, nombre, Icono }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => cx("flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition", isActive ? "bg-brand/15 text-brand" : "text-muted hover:bg-line/50 hover:text-ink")}>
              <Icono size={20} aria-hidden /> {nombre}
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-2 border-t border-line p-4 text-xs text-muted md:flex">
          <BookOpenCheck size={14} aria-hidden />
          <span>Hecho por Jorge Sislema</span>
          <button onClick={alternar} aria-label={oscuro ? "Cambiar a tema claro" : "Cambiar a tema oscuro"} className="ml-auto rounded-lg p-2 hover:bg-line/50 hover:text-ink">
            {oscuro ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
        <p className="px-4 pb-3 text-xs text-muted md:hidden">Hecho por Jorge Sislema</p>
      </aside>
      <main className="min-w-0 flex-1 pb-24"><Outlet /></main>
      <AsistenteFlotante />
    </div>
  );
}
