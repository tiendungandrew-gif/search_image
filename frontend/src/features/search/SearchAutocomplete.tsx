import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { loadSuggestions, type SearchSuggestion } from "./searchSuggestions";

export function SearchAutocomplete({
  value,
  onChange,
  disabled,
  imageOnly = false,
  placeholderText,
  token = "",
  sourceDataset,
}: {
  token?: string;
  sourceDataset?: string;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  imageOnly?: boolean;
  placeholderText?: string;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const input = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<{
    key: string;
    items: SearchSuggestion[];
  } | null>(null);
  const key = JSON.stringify([value.trim(), token, sourceDataset]);
  const suggestions = result?.key === key ? result.items : [];
  useEffect(() => {
    const query = value.trim();
    if (
      !open ||
      disabled ||
      imageOnly ||
      query.length < 2 ||
      query.length > 160
    )
      return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void loadSuggestions(query, controller.signal, token, sourceDataset)
        .then((items) => {
          if (!controller.signal.aborted) setResult({ key, items });
        })
        .catch(() => {
          if (!controller.signal.aborted) setResult({ key, items: [] });
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, open, disabled, imageOnly, token, sourceDataset, key]);
  const expanded = open && !disabled && suggestions.length > 0;
  const activeId =
    expanded && suggestions[active] ? `query-suggestion-${active}` : undefined;
  useEffect(() => {
    if (activeId)
      document.getElementById(activeId)?.scrollIntoView?.({ block: "nearest" });
  }, [activeId]);
  function choose(item: SearchSuggestion) {
    onChange(item.text);
    setOpen(false);
    setActive(-1);
    input.current?.focus();
  }
  return (
    <div className="search-autocomplete">
      <input
        ref={input}
        id="query"
        type="search"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={expanded ? "query-suggestion-list" : undefined}
        aria-activedescendant={activeId}
        aria-describedby="query-hint"
        value={imageOnly ? "" : value}
        disabled={disabled}
        maxLength={2000}
        autoComplete="off"
        spellCheck={false}
        placeholder={
          placeholderText ??
          (imageOnly ? "Đang tìm bằng ảnh tham chiếu" : "Tìm kiếm")
        }
        onChange={(event) => {
          onChange(event.target.value);
          setActive(-1);
          setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          setActive(-1);
        }}
        onBlur={() => {
          setOpen(false);
          setActive(-1);
        }}
        onKeyDown={(event) => {
          if (event.nativeEvent.isComposing) return;
          if (event.key === "ArrowDown" && suggestions.length) {
            event.preventDefault();
            setOpen(true);
            setActive((index) => (index + 1) % suggestions.length);
          } else if (event.key === "ArrowUp" && suggestions.length) {
            event.preventDefault();
            setOpen(true);
            setActive((index) =>
              index <= 0 ? suggestions.length - 1 : index - 1,
            );
          } else if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
            setActive(-1);
          } else if (event.key === "Enter") {
            event.preventDefault();
            if (expanded && suggestions[active]) choose(suggestions[active]);
            else {
              setOpen(false);
              event.currentTarget.form?.requestSubmit();
            }
          }
        }}
      />
      {expanded && (
        <div className="autocomplete-popup">
          <p id="query-suggestion-heading">
            Gợi ý từ thư viện <span>↑ ↓ để chọn · Enter để điền</span>
          </p>
          <ul
            id="query-suggestion-list"
            role="listbox"
            aria-labelledby="query-suggestion-heading"
          >
            {suggestions.map((item, index) => (
              <li
                key={item.text}
                id={`query-suggestion-${index}`}
                role="option"
                aria-selected={active === index}
                onPointerDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(item)}
              >
                <Icon kind="search" />
                <span>
                  <strong>{item.text}</strong>
                  <small>{item.label}</small>
                </span>
                <span className="autocomplete-fill" aria-hidden="true">
                  ↖
                </span>
              </li>
            ))}
          </ul>
          <p className="autocomplete-note">
            Chọn gợi ý hoặc viết bằng tiếng Việt hay tiếng Anh. Bấm tìm kiếm khi
            sẵn sàng.
          </p>
        </div>
      )}
    </div>
  );
}
