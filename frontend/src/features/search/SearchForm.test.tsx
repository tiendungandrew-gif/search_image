import { useState } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { api } from "../../services/api/client";
import type { SearchMode } from "../../types/api";
import type { useSearchSession } from "./useSearchSession";
import { SearchForm } from "./SearchForm";

vi.mock("./searchSuggestions", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./searchSuggestions")>();
  return {
    ...actual,
    loadSuggestions: vi.fn(async () => [
      { text: "a hotel room with an ocean view", label: "Trong thư viện" },
    ]),
  };
});

function setup(headerSearch = false, guest = false, onRequestLogin = vi.fn()) {
  const session: ReturnType<typeof useSearchSession> = {
    state: "IDLE",
    results: null,
    agent: null,
    error: null,
    submittedQuery: "",
    progress: [],
    metrics: {
      started: 0,
      apiMs: null,
      visibleMs: null,
      renderMs: null,
      reactMs: null,
    },
    execute: vi.fn().mockResolvedValue(undefined),
    goToPage: vi.fn(),
    reset: vi.fn(),
    cancel: vi.fn(),
    validationError: vi.fn(),
    markVisible: vi.fn(),
    markReact: vi.fn(),
  };
  const capabilities = {
    text_search: true,
    image_search: !guest,
    multimodal: !guest,
    multi_intent: !guest,
    rerank: !guest,
    explanations: false,
    agent: !guest,
  };
  function Harness() {
    const [mode, setMode] = useState<SearchMode>("auto");
    return (
      <SearchForm
        headerSearch={headerSearch}
        token=""
        onTokenChange={() => undefined}
        authenticated={!guest}
        guest={guest}
        onRequestLogin={onRequestLogin}
        showDiagnostics={false}
        available
        capabilities={capabilities}
        mode={mode}
        onModeChange={setMode}
        session={session}
        datasets={[
          {
            id: "12345678-1234-4234-8234-123456789abc",
            key: "private",
            name: "Thư viện riêng",
          },
        ]}
      />
    );
  }
  render(<Harness />);
  return session;
}

test("suggestions fill and focus the description without submitting a request", async () => {
  const session = setup();
  await userEvent.click(screen.getByRole("button", { name: "Thiên nhiên" }));
  const query = screen.getByLabelText("Bạn đang tìm hình ảnh nào?");
  expect(query).toHaveValue("a forest landscape with mountains");
  expect(query).toHaveFocus();
  expect(session.execute).not.toHaveBeenCalled();
});

test("guests submit text without a token and cannot choose image search", async () => {
  const login = vi.fn();
  const session = setup(true, true, login);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Tìm bằng ảnh" }));
  expect(login).toHaveBeenCalledTimes(1);
  expect(session.execute).not.toHaveBeenCalled();
  expect(
    screen.queryByLabelText("Thêm ảnh tham chiếu"),
  ).not.toBeInTheDocument();
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "con meo",
  );
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.validationError).not.toHaveBeenCalled();
  expect(session.execute).toHaveBeenCalledWith(
    expect.objectContaining({ text: "con meo" }),
    null,
    expect.anything(),
  );
});

test("changing from combined search to description discards the hidden image", async () => {
  const session = setup();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Dùng ảnh" }));
  const file = new File(["unit-fixture"], "reference.png", {
    type: "image/png",
  });
  await user.upload(screen.getByLabelText("Thêm ảnh tham chiếu"), file);
  await user.click(screen.getByRole("button", { name: "Kết hợp" }));
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "coffee",
  );
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ mode: "multimodal", text: "coffee" }),
    file,
    expect.anything(),
  );
  await user.click(screen.getByRole("button", { name: "Mô tả" }));
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ mode: "auto", text: "coffee" }),
    null,
    expect.anything(),
  );
  expect(
    screen.queryByLabelText("Thêm ảnh tham chiếu"),
  ).not.toBeInTheDocument();
});

test("start over clears filters and result count as well as the description", async () => {
  const session = setup();
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "coffee",
  );
  await user.click(screen.getByText("Thư viện và bộ lọc", { exact: true }));
  await user.type(screen.getByLabelText("Thành phố"), "Paris");
  await user.type(screen.getByLabelText(/Thẻ ảnh/), "outdoor");
  await user.click(screen.getByText("Tùy chọn kết quả", { exact: true }));
  await user.clear(screen.getByLabelText("Ảnh mỗi trang"));
  await user.type(screen.getByLabelText("Ảnh mỗi trang"), "3");
  await user.click(screen.getByRole("button", { name: "Bắt đầu lại" }));
  expect(screen.getByLabelText("Bạn đang tìm hình ảnh nào?")).toHaveValue("");
  expect(screen.getByLabelText("Ảnh mỗi trang")).toHaveValue(30);
  await user.click(screen.getByText("Thư viện và bộ lọc", { exact: true }));
  expect(screen.getByLabelText("Thành phố")).toHaveValue("");
  expect(screen.getByLabelText(/Thẻ ảnh/)).toHaveValue("");
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "forest",
  );
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ filters: {}, top_k: 30 }),
    null,
    expect.anything(),
  );
});

test("advanced search modes remain available through result preferences", async () => {
  const session = setup();
  const user = userEvent.setup();
  await user.click(screen.getByText("Tùy chọn kết quả", { exact: true }));
  await user.selectOptions(
    screen.getByLabelText("Cách xử lý yêu cầu"),
    "multi_intent",
  );
  await user.type(
    screen.getByLabelText("Bạn đang tìm hình ảnh nào?"),
    "a red bike and a tree",
  );
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ mode: "multi_intent" }),
    null,
    expect.anything(),
  );
  expect(screen.queryByLabelText("Kết hợp kết quả")).not.toBeInTheDocument();
});

test("toolbar autocomplete chooses a phrase without searching, then Enter submits it", async () => {
  const session = setup(true);
  const user = userEvent.setup();
  const query = screen.getByRole("combobox", {
    name: "Bạn đang tìm hình ảnh nào?",
  });
  await user.type(query, "ho");
  expect(await screen.findByRole("listbox")).toBeVisible();
  await user.keyboard("{ArrowDown}{Enter}");
  expect(query).toHaveValue("a hotel room with an ocean view");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  expect(session.execute).not.toHaveBeenCalled();
  await user.keyboard("{Enter}");
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ text: "a hotel room with an ocean view" }),
    null,
    expect.anything(),
  );
});

test("toolbar options preserve image upload and filter submission", async () => {
  const session = setup(true);
  const user = userEvent.setup();
  expect(
    screen.queryByRole("button", { name: "Dùng ảnh" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tìm bằng ảnh" }));
  const file = new File(["unit-fixture"], "reference.png", {
    type: "image/png",
  });
  await user.upload(screen.getByLabelText("Thêm ảnh tham chiếu"), file);
  await user.click(screen.getByText("Thư viện và bộ lọc", { exact: true }));
  await user.type(screen.getByLabelText("Thành phố"), "Paris");
  await user.click(screen.getByRole("button", { name: "Tìm kiếm ảnh" }));
  expect(session.execute).toHaveBeenLastCalledWith(
    expect.objectContaining({ mode: "image", filters: { city: "Paris" } }),
    file,
    expect.anything(),
  );
  expect(
    screen.getByRole("button", { name: "Tùy chọn tìm kiếm" }),
  ).toHaveAttribute("aria-expanded", "false");
});

test("autocomplete closes on Escape or Tab and pointer selection only fills the draft", async () => {
  const session = setup(true);
  const user = userEvent.setup();
  const query = screen.getByRole("combobox", {
    name: "Bạn đang tìm hình ảnh nào?",
  });
  await user.type(query, "resort");
  await user.keyboard("{ArrowDown}{Escape}");
  expect(query).toHaveValue("resort");
  expect(query).toHaveFocus();
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  await user.type(query, " ");
  expect(await screen.findByRole("listbox")).toBeVisible();
  await user.tab();
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  await user.clear(query);
  await user.type(query, "khach san");
  await user.click((await screen.findAllByRole("option"))[0]);
  expect(query).toHaveValue("a hotel room with an ocean view");
  expect(query).toHaveFocus();
  expect(session.execute).not.toHaveBeenCalled();
});

test("voice search transcribes Vietnamese speech and submits automatically", async () => {
  const instances: FakeSpeechRecognition[] = [];
  class FakeSpeechRecognition {
    lang = "";
    continuous = false;
    interimResults = false;
    maxAlternatives = 1;
    onresult: ((e: unknown) => void) | null = null;
    onerror: ((e: unknown) => void) | null = null;
    onend: (() => void) | null = null;
    start = vi.fn();
    stop = vi.fn(() => {
      this.onend?.();
    });
    constructor() {
      instances.push(this);
    }
  }
  vi.stubGlobal("webkitSpeechRecognition", FakeSpeechRecognition);
  try {
    const session = setup(true);
    const user = userEvent.setup();
    const micButton = screen.getByRole("button", {
      name: "Tìm bằng giọng nói",
    });
    await user.click(micButton);
    expect(micButton).toHaveAttribute("aria-pressed", "true");
    const instance = instances[0];
    expect(instance?.lang).toBe("vi-VN");
    expect(instance?.start).toHaveBeenCalledTimes(1);
    act(() => {
      instance?.onresult?.({
        results: [
          {
            isFinal: true,
            length: 1,
            0: { transcript: "bãi biển hoàng hôn" },
          },
        ],
      });
      instance?.onend?.();
    });
    expect(
      screen.getByRole("combobox", { name: "Bạn đang tìm hình ảnh nào?" }),
    ).toHaveValue("bãi biển hoàng hôn");
    expect(micButton).toHaveAttribute("aria-pressed", "false");
    expect(session.execute).toHaveBeenCalledWith(
      expect.objectContaining({ text: "bãi biển hoàng hôn" }),
      null,
      expect.anything(),
    );
  } finally {
    vi.unstubAllGlobals();
  }
});

test("voice search falls back to MediaRecorder + backend transcription on Firefox", async () => {
  const recorders: FakeMediaRecorder[] = [];
  class FakeMediaRecorder {
    static isTypeSupported = () => true;
    state = "inactive";
    mimeType = "audio/webm";
    ondataavailable: ((e: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    start = vi.fn(() => {
      this.state = "recording";
    });
    stop = vi.fn(() => {
      this.state = "inactive";
      this.ondataavailable?.({
        data: new Blob(["x".repeat(256)], { type: "audio/webm" }),
      });
      this.onstop?.();
    });
    constructor() {
      recorders.push(this);
    }
  }
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }],
      }),
    },
  });
  const transcribeSpy = vi
    .spyOn(api, "transcribeVoice")
    .mockResolvedValue({ transcript: "khách sạn gần biển" });
  try {
    const session = setup(true);
    const user = userEvent.setup();
    const micButton = screen.getByRole("button", {
      name: "Tìm bằng giọng nói",
    });
    await user.click(micButton);
    await waitFor(() =>
      expect(micButton).toHaveAttribute("aria-pressed", "true"),
    );
    expect(recorders[0]?.start).toHaveBeenCalledTimes(1);
    await user.click(micButton);
    await waitFor(() =>
      expect(session.execute).toHaveBeenCalledWith(
        expect.objectContaining({ text: "khách sạn gần biển" }),
        null,
        expect.anything(),
      ),
    );
    expect(transcribeSpy).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("combobox", { name: "Bạn đang tìm hình ảnh nào?" }),
    ).toHaveValue("khách sạn gần biển");
  } finally {
    transcribeSpy.mockRestore();
    vi.unstubAllGlobals();
  }
});
