import { createContext } from "react";
import type { Account } from "../../types/access";
export const CurrentAccountContext = createContext<Account | null>(null);
