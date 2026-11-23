import { StrictMode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { FavoritesProvider } from "./FavoritesProvider";
import { FavoriteButton } from "./FavoriteButton";
import { profileAPI } from "./api";
vi.mock("./api", () => ({ profileAPI: { status: vi.fn(), save: vi.fn() } }));
const id = "12345678-1234-4234-8234-123456789abc";
beforeEach(() => {
  vi.mocked(profileAPI.status).mockResolvedValue([]);
  vi.mocked(profileAPI.save).mockResolvedValue(undefined);
});
afterEach(() => vi.resetAllMocks());
test("batches duplicate buttons and stays functional under StrictMode", async () => {
  render(
    <StrictMode>
      <FavoritesProvider enabled onSignIn={vi.fn()}>
        <FavoriteButton imageId={id} />
        <FavoriteButton imageId={id} />
      </FavoritesProvider>
    </StrictMode>,
  );
  await waitFor(() =>
    expect(profileAPI.status).toHaveBeenCalledWith(
      [id],
      expect.any(AbortSignal),
    ),
  );
  expect(vi.mocked(profileAPI.status).mock.calls[0][1]?.aborted).toBe(false);
  fireEvent.click(screen.getAllByRole("button", { name: "Yêu thích ảnh" })[0]);
  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: "Bỏ yêu thích ảnh" }),
    ).toHaveLength(2),
  );
  expect(profileAPI.save).toHaveBeenCalledWith(id, true);
  fireEvent.click(
    screen.getAllByRole("button", { name: "Bỏ yêu thích ảnh" })[1],
  );
  await waitFor(() =>
    expect(
      screen.getAllByRole("button", { name: "Yêu thích ảnh" }),
    ).toHaveLength(2),
  );
  expect(profileAPI.save).toHaveBeenLastCalledWith(id, false);
});
test("failed saves keep the previous state and show a retryable error", async () => {
  vi.mocked(profileAPI.save).mockRejectedValue(new Error("offline"));
  render(
    <FavoritesProvider enabled onSignIn={vi.fn()}>
      <FavoriteButton imageId={id} />
    </FavoritesProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Yêu thích ảnh" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("offline");
  expect(screen.getByRole("button", { name: "Yêu thích ảnh" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});
test("anonymous users are sent to sign in without writing favorites", () => {
  const signIn = vi.fn();
  render(
    <FavoritesProvider enabled={false} onSignIn={signIn}>
      <FavoriteButton imageId={id} />
    </FavoritesProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Yêu thích ảnh" }));
  expect(signIn).toHaveBeenCalledOnce();
  expect(profileAPI.save).not.toHaveBeenCalled();
});
