import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export const useResumen = () => useQuery({ queryKey: ["resumen"], queryFn: api.resumen });
