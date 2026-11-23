import { filterError, validateImage } from "./validation";

test("upload validates empty, unsupported and oversized files", () => {
  expect(
    validateImage(new File([], "empty.png", { type: "image/png" })),
  ).toContain("rỗng");
  expect(
    validateImage(new File(["x"], "a.svg", { type: "image/svg+xml" })),
  ).toContain("JPEG");
  expect(
    validateImage(new File(["123"], "a.webp", { type: "image/webp" }), 2),
  ).toContain("giới hạn");
  expect(
    validateImage(new File(["ok"], "a.jpeg", { type: "image/jpeg" })),
  ).toBeNull();
});
test("filter validation rejects reversed dimensions and excessive tags", () => {
  expect(filterError({ min_width: 300, max_width: 20 })).toContain("tối thiểu");
  expect(
    filterError({ tags_any: Array.from({ length: 21 }, () => "tag") }),
  ).toContain("20");
  expect(filterError({ min_height: 100, max_height: 100 })).toBeNull();
});
