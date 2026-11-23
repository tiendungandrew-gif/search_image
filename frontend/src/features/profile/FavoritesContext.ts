import { createContext, useContext } from "react";
export interface FavoritesState {
  saved: Record<string, boolean>;
  pending: Set<string>;
  enabled: boolean;
  ensure: (id: string) => void;
  toggle: (id: string) => Promise<void>;
}
export const FavoritesContext = createContext<FavoritesState>({
  saved: {},
  pending: new Set(),
  enabled: false,
  ensure: () => {},
  toggle: async () => {},
});
export const useFavorites = () => useContext(FavoritesContext);
