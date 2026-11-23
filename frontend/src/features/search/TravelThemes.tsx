import { Icon } from "../../components/Icon";
import { travelTopics } from "./travelTheme";

export function TravelThemes({
  onChoose,
  disabled,
  selectedQuery = "",
}: {
  onChoose: (text: string) => void;
  disabled: boolean;
  selectedQuery?: string;
}) {
  return (
    <section
      className="travel-themes"
      id="travel-themes"
      aria-labelledby="travel-themes-heading"
    >
      <div className="travel-themes-heading">
        <div>
          <h2 id="travel-themes-heading">Gợi ý cho bạn</h2>
        </div>
        <p>Chọn chủ đề để điền mô tả tìm kiếm.</p>
      </div>
      <div className="travel-topic-grid">
        {travelTopics.map((topic) => (
          <button
            key={topic.id}
            type="button"
            className="travel-topic"
            aria-label={`Gợi ý: ${topic.label}`}
            disabled={disabled}
            aria-pressed={selectedQuery === topic.text}
            onClick={() => onChoose(topic.text)}
          >
            <span className="travel-topic-icon">
              <Icon kind={topic.icon} />
            </span>
            <span>
              <strong>{topic.label}</strong>
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
