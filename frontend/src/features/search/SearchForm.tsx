import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { api, APIClientError } from "../../services/api/client";
import type {
  HealthSummary,
  SearchMode,
  WorkspaceStatus,
} from "../../types/api";
import { AdvancedControls } from "./AdvancedControls";
import { defaultAdvanced, filterError, validateImage } from "./validation";
import { ImageUpload } from "./ImageUpload";
import { SearchAutocomplete } from "./SearchAutocomplete";
import { travelTopics } from "./travelTheme";
import type { useSearchSession } from "./useSearchSession";
import type { DatasetReference } from "../../types/access";
const modeLabels: Record<SearchMode, string> = {
  auto: "Tự động theo đầu vào",
  text: "Văn bản → Hình ảnh",
  image: "Hình ảnh → Hình ảnh",
  multimodal: "Văn bản + Hình ảnh",
  multi_intent: "Nhiều điều kiện · AND / OR",
  agent: "Agent · Tra cứu nhiều bước",
};
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
}
interface SpeechRecognitionEventLike {
  resultIndex?: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionErrorEventLike {
  error?: string;
}
interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
}
type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;
function getSpeechRecognition(): SpeechRecognitionConstructor | null {
  const scope = globalThis as unknown as {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
}
export function SearchForm({
  token,
  onTokenChange,
  available = false,
  agentAvailable = false,
  capabilities,
  workspace,
  mode,
  onModeChange,
  session,
  authenticated = false,
  guest = false,
  onRequestLogin,
  showDiagnostics = true,
  datasets,
  headerSearch = false,
  queryValue,
  onQueryChange,
}: {
  queryValue?: string;
  onQueryChange?: (value: string) => void;
  headerSearch?: boolean;
  token: string;
  onTokenChange: (value: string) => void;
  available?: boolean;
  agentAvailable?: boolean;
  capabilities?: HealthSummary["capabilities"];
  workspace?: WorkspaceStatus | null;
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
  session: ReturnType<typeof useSearchSession>;
  authenticated?: boolean;
  guest?: boolean;
  onRequestLogin?: () => void;
  showDiagnostics?: boolean;
  datasets?: DatasetReference[];
}) {
  const friendly = (authenticated || guest) && !showDiagnostics;
  const host = useRef<HTMLElement>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [panelView, setPanelView] = useState<"image" | "options">("options");
  const panelVisible = panelOpen || Boolean(session.error);
  const imageDropOnly =
    headerSearch && panelVisible && panelView === "image" && !session.error;
  const [resetVersion, setResetVersion] = useState(0);
  const [localQuery, setLocalQuery] = useState("");
  const query = queryValue ?? localQuery;
  const setQuery = onQueryChange ?? setLocalQuery;
  const [topK, setTopK] = useState(30);
  const [file, setFile] = useState<File | null>(null);
  const [advanced, setAdvanced] = useState(defaultAdvanced);
  const [includeExplanation, setIncludeExplanation] = useState(false);
  const [planner, setPlanner] = useState("deterministic");
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState<{
    text: string;
    isError?: boolean;
  } | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const silenceTimerRef = useRef<number | null>(null);
  const loading = session.state === "SEARCHING";
  const caps = workspace?.capabilities ?? capabilities;
  const supported: Record<SearchMode, boolean> = {
    auto: caps ? caps.text_search || caps.image_search : available,
    text: caps?.text_search ?? available,
    image: caps?.image_search ?? available,
    multimodal: caps?.multimodal ?? available,
    multi_intent: caps?.multi_intent ?? available,
    agent: caps?.agent ?? agentAvailable,
  };
  const ragAvailable = caps?.explanations ?? false;
  const rerankAvailable = caps?.rerank ?? available;
  const maxK = workspace?.limits.top_k ?? 50;
  const maxBytes = workspace?.limits.image_bytes ?? 20 * 1024 ** 2;
  const imageMode = ["image", "multimodal", "auto"].includes(mode);
  const usesImage = imageMode && file !== null;
  const combined = usesImage && mode !== "image" && query.trim().length > 0;
  const inputsReady =
    mode === "multimodal"
      ? file && query.trim()
      : mode === "image"
        ? file
        : mode === "auto"
          ? file || query.trim()
          : query.trim();
  useEffect(() => {
    if (friendly && session.error)
      document.getElementById("search-form-error")?.focus();
  }, [friendly, session.error]);
  useEffect(() => {
    if (!headerSearch) return;
    const dismiss = (event: PointerEvent) => {
      if (event.target instanceof Node && !host.current?.contains(event.target))
        setPanelOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [headerSearch]);
  function cleanupVoiceCapture() {
    if (silenceTimerRef.current !== null) {
      window.clearInterval(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state !== "inactive"
    ) {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        /* Recorder already stopped. */
      }
    }
    mediaRecorderRef.current = null;
    if (mediaStreamRef.current) {
      for (const track of mediaStreamRef.current.getTracks()) track.stop();
      mediaStreamRef.current = null;
    }
  }
  useEffect(
    () => () => {
      recognitionRef.current?.abort?.();
      recognitionRef.current?.stop();
      recognitionRef.current = null;
      cleanupVoiceCapture();
    },
    [],
  );
  function changeMode(next: SearchMode) {
    session.reset();
    if (friendly && ["auto", "text", "multi_intent", "agent"].includes(next))
      setFile(null);
    onModeChange(next);
  }
  async function submit(overrideText?: string) {
    const activeMode: SearchMode =
      overrideText !== undefined && mode === "image" ? "auto" : mode;
    const activeQuery = (overrideText ?? query).trim();
    const activeImageMode = ["image", "multimodal", "auto"].includes(
      activeMode,
    );
    const activeUsesImage =
      activeImageMode &&
      file !== null &&
      !(overrideText !== undefined && mode === "image");
    const activeCombined =
      activeUsesImage && activeMode !== "image" && activeQuery.length > 0;
    const activeInputsReady =
      activeMode === "multimodal"
        ? file && activeQuery
        : activeMode === "image"
          ? file
          : activeMode === "auto"
            ? activeUsesImage || activeQuery
            : activeQuery;
    if (!token.trim() && !authenticated && !guest)
      return session.validationError("Nhập token truy cập trước khi tìm kiếm.");
    if (!supported[activeMode])
      return session.validationError(
        "Phương thức này chưa sẵn sàng. Kiểm tra trạng thái dataset.",
      );
    if (!activeInputsReady)
      return session.validationError(
        "Bổ sung văn bản hoặc ảnh theo phương thức đã chọn.",
      );
    if (
      activeQuery.length > 2000 ||
      topK < 1 ||
      topK > maxK ||
      !Number.isInteger(topK)
    )
      return session.validationError(
        `Truy vấn tối đa 2000 ký tự; số kết quả từ 1 đến ${maxK}.`,
      );
    const issue = activeMode === "agent" ? null : filterError(advanced.filters);
    if (issue) return session.validationError(issue);
    if (activeUsesImage && file) {
      const issue = validateImage(file, maxBytes);
      if (issue) return session.validationError(issue);
    }
    if (
      activeMode === "auto" &&
      ((activeCombined && !supported.multimodal) ||
        (activeUsesImage && !supported.image) ||
        (!activeUsesImage && !supported.text))
    )
      return session.validationError(
        "Backend chưa hỗ trợ loại đầu vào này. Chọn phương thức đang khả dụng.",
      );
    if (headerSearch) setPanelOpen(false);
    await session.execute(
      {
        mode: activeMode,
        ...(activeMode !== "image" && activeQuery ? { text: activeQuery } : {}),
        top_k: topK,
        rerank: {
          enabled: advanced.rerank && rerankAvailable,
          on_failure: "skip",
        },
        ...(activeMode !== "agent" ? { filters: advanced.filters } : {}),
        ...(activeCombined
          ? {
              fusion: {
                method: advanced.fusion,
                text_weight: advanced.textWeight,
                image_weight: 1 - advanced.textWeight,
              },
            }
          : {}),
      },
      activeUsesImage ? file : null,
      {
        includeExplanation: includeExplanation && ragAvailable,
        planner:
          planner === "llm" && workspace?.agent.llm_planning === false
            ? "deterministic"
            : planner,
      },
    );
  }
  function toggleVoiceSearch() {
    if (listening) {
      setListening(false);
      recognitionRef.current?.stop();
      cleanupVoiceCapture();
      return;
    }
    if (transcribing) return;
    setVoiceMessage(null);
    if (session.error) session.reset();
    if (mode === "image") changeMode("auto");
    const canRecordMedia =
      typeof navigator !== "undefined" &&
      Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof MediaRecorder !== "undefined";
    const Recognition = getSpeechRecognition();
    if (!canRecordMedia && !Recognition) {
      const msg = "Trình duyệt này chưa hỗ trợ tìm kiếm bằng giọng nói.";
      setVoiceMessage({ text: msg, isError: true });
      session.validationError(msg);
      return;
    }
    if (canRecordMedia && !Recognition) {
      void startMediaVoiceCapture();
      return;
    }
    if (!Recognition) return;
    const recognition = new Recognition();
    recognition.lang = "vi-VN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    let latestTranscript = "";
    let hadError = false;
    recognition.onresult = (event) => {
      const pieces: string[] = [];
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result?.[0]?.transcript?.trim();
        if (transcript) pieces.push(transcript);
      }
      const combinedText = pieces.join(" ").trim();
      if (combinedText) {
        latestTranscript = combinedText;
        setQuery(combinedText);
      }
    };
    recognition.onerror = (event) => {
      hadError = true;
      setListening(false);
      recognitionRef.current = null;
      if (event.error === "aborted") return;
      if (
        canRecordMedia &&
        (event.error === "network" ||
          event.error === "service-not-allowed" ||
          event.error === "language-not-supported")
      ) {
        void startMediaVoiceCapture();
        return;
      }
      const message =
        event.error === "not-allowed" || event.error === "service-not-allowed"
          ? "Chưa có quyền truy cập micro. Hãy cấp quyền micro trên trình duyệt."
          : event.error === "no-speech"
            ? "Chưa nhận được giọng nói. Hãy thử nói lại gần micro hơn."
            : "Không nhận diện được giọng nói. Vui lòng thử lại.";
      setVoiceMessage({ text: message, isError: true });
      session.validationError(message);
    };
    recognition.onend = () => {
      setListening(false);
      if (recognitionRef.current === recognition) {
        recognitionRef.current = null;
      }
      if (!hadError && latestTranscript) {
        setVoiceMessage(null);
        document.getElementById("query")?.focus();
        void submit(latestTranscript);
      }
    };
    try {
      recognitionRef.current = recognition;
      setListening(true);
      setVoiceMessage({
        text: "Đang nghe… Hãy nói từ khóa tìm kiếm (bấm lại micro khi xong).",
      });
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setListening(false);
      if (canRecordMedia) {
        void startMediaVoiceCapture();
        return;
      }
      const msg = "Không thể khởi động micro. Vui lòng thử lại.";
      setVoiceMessage({ text: msg, isError: true });
      session.validationError(msg);
    }
  }
  async function startMediaVoiceCapture() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const mimeType =
        typeof MediaRecorder.isTypeSupported === "function"
          ? ([
              "audio/webm;codecs=opus",
              "audio/webm",
              "audio/ogg;codecs=opus",
              "audio/ogg",
              "audio/mp4",
            ].find((t) => MediaRecorder.isTypeSupported(t)) ?? "")
          : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      const chunks: BlobPart[] = [];
      let peakLevel = 0;
      let audioCtx: AudioContext | null = null;
      const AudioCtx =
        typeof window !== "undefined"
          ? window.AudioContext ||
            (window as unknown as { webkitAudioContext?: typeof AudioContext })
              .webkitAudioContext
          : undefined;
      if (AudioCtx) {
        try {
          audioCtx = new AudioCtx();
          const source = audioCtx.createMediaStreamSource(stream);
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 512;
          source.connect(analyser);
          const samples = new Uint8Array(analyser.fftSize);
          let spokenAt = 0;
          const startedAt = performance.now();
          silenceTimerRef.current = window.setInterval(() => {
            analyser.getByteTimeDomainData(samples);
            let sum = 0;
            for (let i = 0; i < samples.length; i += 1) {
              const norm = (samples[i] - 128) / 128;
              sum += norm * norm;
            }
            const rms = Math.sqrt(sum / samples.length);
            if (rms > peakLevel) peakLevel = rms;
            const now = performance.now();
            if (rms > 0.025) {
              spokenAt = now;
            }
            if (
              (spokenAt > 0 && now - spokenAt > 1400) ||
              now - startedAt > 8000
            ) {
              cleanupVoiceCapture();
            }
          }, 100);
        } catch {
          /* Fallback to timeout + manual stop if AudioContext is restricted. */
        }
      }
      if (silenceTimerRef.current === null) {
        silenceTimerRef.current = window.setTimeout(() => {
          cleanupVoiceCapture();
        }, 6000);
      }
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = async () => {
        setListening(false);
        if (audioCtx) {
          void audioCtx.close().catch(() => undefined);
        }
        for (const track of stream.getTracks()) track.stop();
        if (mediaStreamRef.current === stream) mediaStreamRef.current = null;
        const blob = new Blob(chunks, {
          type: recorder.mimeType || "audio/webm",
        });
        if (
          blob.size < 128 ||
          (AudioCtx && peakLevel > 0 && peakLevel < 0.008)
        ) {
          const msg =
            "Chưa nhận được giọng nói. Hãy thử nói lại gần micro hơn.";
          setVoiceMessage({ text: msg, isError: true });
          return;
        }
        setTranscribing(true);
        setVoiceMessage({ text: "Đang nhận diện giọng nói…" });
        try {
          const { transcript } = await api.transcribeVoice(blob, token);
          const clean = transcript.trim();
          if (!clean) {
            setVoiceMessage({
              text: "Chưa nghe rõ từ khóa. Bạn hãy bấm micro và nói lại nhé.",
              isError: true,
            });
            return;
          }
          setVoiceMessage(null);
          setQuery(clean);
          document.getElementById("query")?.focus();
          await submit(clean);
        } catch (err) {
          const msg =
            err instanceof Error
              ? err.message
              : "Không thể nhận diện giọng nói lúc này.";
          setVoiceMessage({ text: msg, isError: true });
        } finally {
          setTranscribing(false);
        }
      };
      setListening(true);
      setVoiceMessage({
        text: "Đang nghe… Hãy nói từ khóa tìm kiếm (bấm lại micro khi xong).",
      });
      recorder.start(200);
    } catch {
      cleanupVoiceCapture();
      setListening(false);
      const msg =
        "Chưa có quyền truy cập micro. Hãy chọn Cho phép (Allow) khi trình duyệt hỏi quyền micro.";
      setVoiceMessage({ text: msg, isError: true });
    }
  }
  const friendlyLabels: Record<SearchMode, string> = {
    auto: "Tự động chọn cách tìm",
    text: "Tìm bằng mô tả",
    image: "Tìm ảnh tương tự",
    multimodal: "Kết hợp ảnh và mô tả",
    multi_intent: "Tìm theo nhiều điều kiện",
    agent: "Tìm theo mối liên hệ",
  };
  const modeControl = (
    <div className="mode-field">
      <label htmlFor="mode">
        {friendly ? "Cách xử lý yêu cầu" : "Phương thức"}
      </label>
      <select
        id="mode"
        value={mode}
        disabled={friendly && loading}
        onChange={(e) => changeMode(e.target.value as SearchMode)}
      >
        {Object.entries(friendly ? friendlyLabels : modeLabels).map(
          ([key, label]) => (
            <option
              key={key}
              value={key}
              disabled={key !== "auto" && !supported[key as SearchMode]}
            >
              {label}
              {!supported[key as SearchMode] ? " · chưa sẵn sàng" : ""}
            </option>
          ),
        )}
      </select>
    </div>
  );
  const countControl = (
    <div className="top-k-field">
      <label htmlFor="top-k">
        {mode === "agent" ? "Số kết quả" : "Ảnh mỗi trang"}
      </label>
      <input
        id="top-k"
        type="number"
        min={1}
        max={maxK}
        step={1}
        value={topK}
        disabled={friendly && loading}
        onChange={(e) => setTopK(Number(e.target.value))}
      />
    </div>
  );
  const queryControl = (
    <div
      className="query-entry"
      hidden={friendly && mode === "image" && !headerSearch}
    >
      <label className="field-label" htmlFor="query">
        Bạn đang tìm hình ảnh nào?
      </label>
      {friendly ? (
        <SearchAutocomplete
          token={token}
          sourceDataset={advanced.filters?.source_dataset}
          value={query}
          onChange={(value) => {
            setQuery(value);
            if (voiceMessage) setVoiceMessage(null);
            if (headerSearch) setPanelOpen(false);
            if (session.error) session.reset();
          }}
          disabled={mode === "image" || loading}
          imageOnly={mode === "image"}
          placeholderText={
            listening
              ? "Đang nghe… Hãy nói từ khóa (bấm lại micro khi xong)"
              : transcribing
                ? "Đang nhận diện giọng nói…"
                : undefined
          }
        />
      ) : (
        <textarea
          id="query"
          value={query}
          disabled={mode === "image" || (friendly && loading)}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={2000}
          placeholder={
            friendly
              ? "Thử: a peaceful beach at sunset…"
              : "Ví dụ: Một quán cà phê bên cửa sổ, trong ánh nắng sớm…"
          }
          rows={friendly ? 1 : 3}
          aria-describedby="query-hint"
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              if (!loading) e.currentTarget.form?.requestSubmit();
            }
          }}
        />
      )}
      <div id="query-hint" className="input-caption">
        <span>
          {friendly
            ? "Tìm bằng tiếng Việt hoặc tiếng Anh, theo cách bạn mô tả."
            : "Enter để tìm · Shift + Enter để xuống dòng"}
        </span>
        <span aria-label={`${query.length} trên 2000 ký tự`}>
          {query.length} / 2000
        </span>
      </div>
    </div>
  );
  const searchButton = (
    <button
      className="search-button"
      aria-label={loading ? "Đang tìm kiếm…" : "Tìm kiếm ảnh"}
      type="submit"
      disabled={
        !supported[mode] ||
        (!authenticated && !guest && !token.trim()) ||
        loading ||
        !inputsReady
      }
      aria-describedby="search-unavailable"
    >
      <Icon kind="search" />
      <span className="search-button-label">
        {loading ? "Đang tìm kiếm…" : "Tìm kiếm ảnh"}
      </span>
      <Icon kind="arrow" />
    </button>
  );
  const voiceButton = (
    <button
      type="button"
      className="navbar-voice-button"
      aria-label="Tìm bằng giọng nói"
      aria-pressed={listening}
      title={
        listening
          ? "Đang nghe giọng nói… Bấm để dừng"
          : transcribing
            ? "Đang nhận diện giọng nói…"
            : "Tìm bằng giọng nói"
      }
      disabled={loading || transcribing || !supported.text}
      onClick={toggleVoiceSearch}
    >
      <Icon kind="mic" />
    </button>
  );
  return (
    <section
      ref={host}
      onBlur={(event) => {
        if (
          headerSearch &&
          event.relatedTarget instanceof Node &&
          !event.currentTarget.contains(event.relatedTarget)
        )
          setPanelOpen(false);
      }}
      className={`search-card ${friendly ? "simple-search-card" : ""}`}
      aria-labelledby="search-heading"
    >
      <div className="card-kicker">
        <span className="accent-dot" />
        {friendly ? "BẮT ĐẦU TỪ ĐIỀU BẠN NHỚ" : "KHÔNG GIAN TÌM KIẾM"}
        <span className="soon-badge">
          {supported[mode]
            ? friendly
              ? "Sẵn sàng"
              : "Sẵn sàng khám phá"
            : friendly
              ? "Đang chuẩn bị"
              : "Đang chờ chỉ mục"}
        </span>
      </div>
      <h2 id="search-heading" tabIndex={-1}>
        {friendly ? "Tìm kiếm theo cách của bạn" : "Bắt đầu bằng một ý tưởng."}
      </h2>
      <p className="muted">
        {friendly
          ? "Một mô tả ngắn hoặc một bức ảnh là đủ để bắt đầu."
          : "Mô tả điều bạn đang tìm hoặc chọn một ảnh làm điểm xuất phát."}
      </p>
      <form
        className={friendly ? "consumer-search-form" : undefined}
        data-input-mode={mode}
        noValidate={friendly}
        aria-label="Tìm kiếm hình ảnh"
        aria-busy={loading}
        onKeyDown={(event) => {
          if (headerSearch && event.key === "Escape" && panelVisible) {
            event.preventDefault();
            setPanelOpen(false);
            if (session.error) session.reset();
            document.getElementById("navbar-search-options-toggle")?.focus();
          }
        }}
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {headerSearch && (
          <div className="navbar-search-line">
            {searchButton}
            {queryControl}
            {voiceButton}
            <button
              type="button"
              className="navbar-image-button"
              aria-label="Tìm bằng ảnh"
              aria-expanded={headerSearch ? imageDropOnly : undefined}
              title={guest ? "Đăng nhập để tìm bằng ảnh" : "Tìm bằng ảnh"}
              disabled={loading || (!guest && !supported.image)}
              onClick={() => {
                if (guest) {
                  onRequestLogin?.();
                  return;
                }
                if (panelOpen && panelView === "image") {
                  setPanelOpen(false);
                  return;
                }
                changeMode("image");
                setPanelView("image");
                setPanelOpen(true);
              }}
            >
              <Icon kind="camera" />
            </button>
            <button
              id="navbar-search-options-toggle"
              type="button"
              className="navbar-options-button"
              aria-label="Tùy chọn tìm kiếm"
              aria-expanded={panelVisible && !imageDropOnly}
              aria-controls="navbar-search-panel"
              onClick={() => {
                if (session.error) session.reset();
                if (panelOpen && panelView === "image") {
                  if (!file && mode === "image") changeMode("auto");
                  setPanelView("options");
                  return;
                }
                setPanelView("options");
                setPanelOpen(!panelOpen);
              }}
            >
              <Icon kind="sliders" />
            </button>
          </div>
        )}
        {voiceMessage && (
          <p
            role="status"
            className={`voice-status-banner${voiceMessage.isError ? " is-error" : ""}`}
          >
            {voiceMessage.text}
          </p>
        )}
        <div
          className={
            headerSearch
              ? `navbar-search-panel${imageDropOnly ? " is-image-drop-panel" : ""}`
              : "search-fields"
          }
          id={headerSearch ? "navbar-search-panel" : undefined}
          hidden={headerSearch && !panelVisible}
        >
          {headerSearch && (
            <div className="navbar-panel-heading">
              <strong>
                {imageDropOnly
                  ? "Tìm kiếm bằng hình ảnh"
                  : "Tùy chỉnh cách tìm ảnh"}
              </strong>
              <button
                type="button"
                aria-label="Đóng tùy chọn tìm kiếm"
                onClick={() => {
                  if (session.error) session.reset();
                  setPanelOpen(false);
                }}
              >
                ✕
              </button>
            </div>
          )}
          {headerSearch && loading && (
            <button
              type="button"
              className="cancel-button"
              onClick={session.cancel}
            >
              Hủy tìm kiếm
            </button>
          )}
          {headerSearch && (
            <p className="navbar-language-note">
              Tìm bằng tiếng Việt hoặc tiếng Anh, theo cách bạn mô tả.
            </p>
          )}
          {friendly && (
            <div
              className="search-methods"
              role="group"
              aria-label="Cách tìm ảnh"
            >
              {(
                [
                  ["auto", "Mô tả", "search"],
                  ["image", "Dùng ảnh", "image"],
                  ["multimodal", "Kết hợp", "layers"],
                ] as const
              ).map(([key, label, icon]) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={
                    mode === key || (key === "auto" && mode === "text")
                  }
                  disabled={loading || !supported[key]}
                  onClick={() => changeMode(key)}
                >
                  <Icon kind={icon} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          )}
          {!authenticated && !guest && (
            <>
              <label className="field-label" htmlFor="search-token">
                Token truy cập
              </label>
              <input
                id="search-token"
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={token}
                onChange={(e) => onTokenChange(e.target.value)}
              />
              <p className="field-hint">
                Token chỉ giữ trong phiên này, không lưu trên trình duyệt.
              </p>
            </>
          )}
          {!headerSearch && queryControl}
          {friendly && ["auto", "text"].includes(mode) && (
            <div className="query-suggestions">
              <span>Gợi ý:</span>
              {travelTopics.slice(0, 3).map(({ label, text }) => (
                <button
                  type="button"
                  key={text}
                  disabled={loading}
                  onClick={() => {
                    session.reset();
                    if (headerSearch) setPanelOpen(false);
                    setQuery(text);
                    document.getElementById("query")?.focus();
                  }}
                >
                  {label}
                  <span aria-hidden="true"> ↗</span>
                </button>
              ))}
            </div>
          )}
          {friendly && ["image", "multimodal"].includes(mode) && (
            <div className="simple-image-input">
              <p className="mode-hint">
                {imageDropOnly
                  ? "Kéo thả ảnh vào khung bên dưới hoặc bấm để chọn file ảnh từ máy tính."
                  : mode === "image"
                    ? "Chọn một ảnh để tìm những hình ảnh có nội dung gần giống."
                    : "Thêm ảnh tham chiếu và mô tả điều bạn muốn tìm."}
              </p>
              <ImageUpload
                file={file}
                onChange={setFile}
                maxBytes={maxBytes}
                disabled={loading}
              />
              {imageDropOnly && file && (
                <button
                  type="submit"
                  className="primary-button image-drop-submit"
                  disabled={loading}
                >
                  {loading ? "Đang tìm kiếm…" : "Tìm ảnh tương tự ngay"}
                </button>
              )}
            </div>
          )}
          {!friendly && (
            <div className="form-row">
              {modeControl}
              {countControl}
              {voiceButton}
              {searchButton}
            </div>
          )}
          {mode === "agent" && (
            <div className="advanced-controls">
              {showDiagnostics && (
                <>
                  <label className="field-label" htmlFor="agent-planner">
                    Lập kế hoạch
                  </label>
                  <select
                    id="agent-planner"
                    value={planner}
                    onChange={(e) => setPlanner(e.target.value)}
                  >
                    <option value="deterministic">Theo mẫu đã hỗ trợ</option>
                    <option
                      value="llm"
                      disabled={workspace?.agent.llm_planning === false}
                    >
                      LLM có kiểm tra kế hoạch
                    </option>
                  </select>
                </>
              )}
              <label className="rerank-control">
                <input
                  type="checkbox"
                  disabled={!ragAvailable || loading}
                  checked={includeExplanation && ragAvailable}
                  onChange={(e) => setIncludeExplanation(e.target.checked)}
                />
                Giải thích sau khi tìm ảnh
              </label>
              <p className="muted">
                {friendly
                  ? "Tìm theo quan hệ có nguồn trong thư viện, như địa danh và thành phố."
                  : "Agent tra cứu quan hệ có nguồn và chỉ hiển thị các bước công khai."}
              </p>
            </div>
          )}
          {!friendly && imageMode && (
            <ImageUpload file={file} onChange={setFile} maxBytes={maxBytes} />
          )}
          {friendly && !headerSearch && (
            <div className="primary-search-actions">
              {searchButton}
              {voiceButton}
              {loading && (
                <button
                  type="button"
                  className="cancel-button"
                  onClick={session.cancel}
                >
                  {mode === "agent" ? "Dừng tìm kiếm" : "Hủy tìm kiếm"}
                </button>
              )}
            </div>
          )}
          <div className={friendly ? "search-refinements" : undefined}>
            {friendly && (
              <details className="search-preferences">
                <summary>Tùy chọn kết quả</summary>
                <p>
                  Điều chỉnh số ảnh hoặc chọn cách tìm phù hợp với yêu cầu phức
                  tạp hơn.
                </p>
                <div className="form-row">
                  {modeControl}
                  {countControl}
                </div>
              </details>
            )}
            <AdvancedControls
              key={resetVersion}
              value={advanced}
              onChange={setAdvanced}
              fusionAvailable={combined && supported.multimodal}
              rerankAvailable={rerankAvailable}
              disabled={mode === "agent" || (friendly && loading)}
              datasets={datasets}
              simple={friendly}
            />
            <div className="search-actions">
              <button
                type="button"
                className="text-button"
                onClick={() => {
                  session.reset();
                  setQuery("");
                  setFile(null);
                  if (friendly) {
                    setAdvanced(defaultAdvanced);
                    setResetVersion((n) => n + 1);
                    setTopK(30);
                    setPlanner("deterministic");
                    setIncludeExplanation(false);
                    onModeChange("auto");
                    requestAnimationFrame(() =>
                      document.getElementById("query")?.focus(),
                    );
                  }
                }}
              >
                {friendly ? "Bắt đầu lại" : "Xóa truy vấn"}
              </button>
              {!friendly && loading && (
                <button
                  type="button"
                  className="cancel-button"
                  onClick={session.cancel}
                >
                  {mode === "agent" ? "Dừng Agent" : "Hủy tìm kiếm"}
                </button>
              )}
              <span className="keyboard-hint">
                {friendly ? "Enter để tìm · Shift + Enter để xuống dòng" : ""}
              </span>
            </div>
          </div>
          {session.error && (
            <div
              id="search-form-error"
              tabIndex={-1}
              role="alert"
              className="error-message"
            >
              <p>{session.error.message}</p>
              {showDiagnostics && session.error instanceof APIClientError && (
                <small>
                  Mã: {session.error.code}
                  {session.error.requestId
                    ? ` · Request: ${session.error.requestId}`
                    : ""}
                </small>
              )}
              <p>
                {friendly
                  ? "Bạn có thể kiểm tra mô tả hoặc bộ lọc rồi thử lại."
                  : "Kiểm tra đầu vào, kết nối hoặc quyền truy cập rồi gửi lại khi sẵn sàng."}
              </p>
              {friendly && (
                <button
                  type="button"
                  className="secondary-button"
                  disabled={loading}
                  onClick={() => void submit()}
                >
                  Thử tìm lại
                </button>
              )}
            </div>
          )}
        </div>
      </form>
      <p id="search-unavailable" className="availability-note">
        <span className="note-symbol" aria-hidden="true">
          i
        </span>
        {supported[mode]
          ? friendly
            ? "Kết quả chỉ lấy từ những thư viện bạn được chia sẻ."
            : "Tìm bằng văn bản, ảnh hoặc kết hợp. Điểm xếp hạng không phải xác suất; điều kiện chưa xác minh sẽ được ghi rõ."
          : authenticated
            ? "Thư viện tìm kiếm hiện chưa sẵn sàng. Vui lòng thử lại sau hoặc liên hệ quản trị viên."
            : "Tìm kiếm chưa sẵn sàng. Kiểm tra model và active index."}
      </p>
    </section>
  );
}
