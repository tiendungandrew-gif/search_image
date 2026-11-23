/** Suppress import placeholders; never infer missing location or usage rights. */
export function displayMetadata(
  value: string | null | undefined,
): string | null {
  const text = value?.trim();
  if (
    !text ||
    /^(unknown|unspecified|not specified(?: in source csv)?|n\/?a|null|none|chưa có thông tin)$/i.test(
      text,
    )
  )
    return null;
  return text;
}
