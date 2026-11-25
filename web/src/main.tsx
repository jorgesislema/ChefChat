import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import { Layout } from "./components/Layout";
import Inicio from "./pages/Inicio";
import Manuales from "./pages/Manuales";
import Inventario from "./pages/Inventario";
import Mermas from "./pages/Mermas";
import Capacitacion from "./pages/Capacitacion";
import Panel from "./pages/Panel";
import Proveedores from "./pages/Proveedores";
import Compras from "./pages/Compras";
import Turno from "./pages/Turno";
import Recetas from "./pages/Recetas";
import Menu from "./pages/Menu";

const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Inicio />} />
            <Route path="manuales" element={<Manuales />} />
            <Route path="inventario" element={<Inventario />} />
            <Route path="proveedores" element={<Proveedores />} />
            <Route path="compras" element={<Compras />} />
            <Route path="turno" element={<Turno />} />
            <Route path="recetas" element={<Recetas />} />
            <Route path="menu" element={<Menu />} />
            <Route path="mermas" element={<Mermas />} />
            <Route path="capacitacion" element={<Capacitacion />} />
            <Route path="panel" element={<Panel />} />
            <Route path="*" element={<Inicio />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
