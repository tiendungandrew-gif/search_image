import { decodeSuggestions } from "./searchSuggestions";

test("decodes actual catalog suggestions without translating their names", () => {
  expect(
    decodeSuggestions({
      suggestions: [{ text: "Phở 10 Lý Quốc Sư", label: "Trong thư viện" }],
    }),
  ).toEqual([{ text: "Phở 10 Lý Quốc Sư", label: "Trong thư viện" }]);
  expect(decodeSuggestions({ suggestions: [] })).toEqual([]);
});

test("rejects malformed or unbounded responses", () => {
  for (const value of [
    null,
    {},
    { suggestions: [{ text: 1, label: "x" }] },
    { suggestions: Array(9).fill({ text: "Khách sạn", label: "x" }) },
  ]) {
    expect(() => decodeSuggestions(value)).toThrow();
  }
});
