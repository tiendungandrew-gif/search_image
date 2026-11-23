import { api, APIClientError } from "../../services/api/client";
import { record } from "../../services/api/decoders";

export interface SearchSuggestion {
  text: string;
  label: string;
}

export function decodeSuggestions(value: unknown): SearchSuggestion[] {
  if (
    !record(value) ||
    !Array.isArray(value.suggestions) ||
    value.suggestions.length > 8 ||
    !value.suggestions.every(
      (item) =>
        record(item) &&
        typeof item.text === "string" &&
        item.text.length >= 2 &&
        item.text.length <= 256 &&
        typeof item.label === "string" &&
        item.label.length <= 120,
    )
  ) {
    throw new APIClientError(
      "INVALID_RESPONSE",
      "Gợi ý tìm kiếm không hợp lệ.",
    );
  }
  return value.suggestions as SearchSuggestion[];
}

export function loadSuggestions(
  query: string,
  signal: AbortSignal,
  token = "",
  sourceDataset?: string,
) {
  const params = new URLSearchParams({ q: query });
  if (sourceDataset) params.set("source_dataset", sourceDataset);
  return api.request(`/search/suggestions?${params}`, decodeSuggestions, {
    signal,
    token,
    timeout: 5000,
  });
}
