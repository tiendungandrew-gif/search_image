import type { Constraint, SearchResponse } from "../../types/api";

function ConstraintTree({ clause }: { clause: Constraint }) {
  if ("op" in clause)
    return (
      <li>
        <strong>{clause.op.toUpperCase()}</strong>
        <ul>
          {clause.clauses.map((child, i) => (
            <ConstraintTree clause={child} key={i} />
          ))}
        </ul>
      </li>
    );
  return (
    <li>
      <code>{clause.id}</code> ·{" "}
      {clause.kind === "semantic" ? clause.text : JSON.stringify(clause.filter)}{" "}
      {clause.required ? "· bắt buộc" : ""}
    </li>
  );
}
export function QueryAnalysis({ response }: { response: SearchResponse }) {
  if (!response.query_analysis) return null;
  const analysis = response.query_analysis;
  return (
    <details
      className="query-analysis"
      data-testid="query-analysis"
      open={response.search_mode === "multi_intent"}
    >
      <summary>
        Phân tích truy vấn · {analysis.query_type} · {analysis.language}
      </summary>
      <p>
        {analysis.uncertain
          ? "Phân tích chưa chắc chắn"
          : "Phân tích theo mẫu được backend hỗ trợ"}{" "}
        · {response.effective_settings?.route}
      </p>
      {analysis.constraints && (
        <ul aria-label="Cây điều kiện từ backend">
          <ConstraintTree clause={analysis.constraints} />
        </ul>
      )}
      {analysis.limitations.map((item, i) => (
        <p key={i}>{item}</p>
      ))}
    </details>
  );
}
