/**
 * Подготовка настроек модели для движка: маппинг читается рядом с моделью, выражения из него
 * дописываются в `FileReferences.Expressions` model3.json — у многих моделей (Haru в том числе)
 * файлы выражений есть, а в манифесте не перечислены.
 */
import { DEFAULT_MAPPING, parseMapping, type AvatarMapping } from "../mapping";

export type Fetcher = (
  url: string,
) => Promise<Pick<Response, "ok" | "status" | "json"> & { headers: Pick<Headers, "get"> }>;

const browserFetch: Fetcher = (url) => fetch(url);

/**
 * Файл есть и это JSON. Dev-сервер Vite (и SPA-резерв вообще) на отсутствующий путь отвечает
 * index.html с кодом 200 — такой ответ равен «файла нет», а не «битый JSON».
 */
function isJsonFile(response: Awaited<ReturnType<Fetcher>>): boolean {
  return response.ok && (response.headers.get("content-type") ?? "").includes("json");
}

/** `mapping.json` модели; нет файла — модель как есть, битый файл — ошибка с полем. */
export async function loadMapping(
  url: string,
  fetcher: Fetcher = browserFetch,
): Promise<AvatarMapping> {
  const response = await fetcher(url);
  if (response.status === 404 || (response.ok && !isJsonFile(response))) {
    return DEFAULT_MAPPING;
  }
  if (!response.ok) {
    throw new Error(`mapping.json: HTTP ${String(response.status)}`);
  }
  const raw: unknown = await response.json();
  return parseMapping(raw);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Копия model3.json с выражениями маппинга (поверх одноимённых из манифеста) и `url` — по нему
 * движок разрешает относительные пути файлов модели, когда настройки переданы объектом.
 */
export function withExpressions(
  model3: unknown,
  url: string,
  expressions: Record<string, string>,
): Record<string, unknown> {
  if (!isRecord(model3) || !isRecord(model3.FileReferences)) {
    throw new Error("model3.json: нет FileReferences — это не манифест модели Cubism 3+");
  }
  const refs = model3.FileReferences;
  const declared = Array.isArray(refs.Expressions) ? refs.Expressions.filter(isRecord) : [];
  const ours = new Set(Object.keys(expressions));
  const kept = declared.filter((item) => typeof item.Name !== "string" || !ours.has(item.Name));
  const added = Object.entries(expressions).map(([Name, File]) => ({ Name, File }));
  return {
    ...model3,
    url,
    FileReferences: { ...refs, Expressions: [...kept, ...added] },
  };
}

/** Манифест модели с выражениями из маппинга — готов для `Live2DModel.from`. */
export async function loadSettings(
  modelUrl: string,
  mapping: AvatarMapping,
  fetcher: Fetcher = browserFetch,
): Promise<Record<string, unknown>> {
  const response = await fetcher(modelUrl);
  if (!isJsonFile(response)) {
    throw new Error(`нет файла модели ${modelUrl} (ui/public/avatars/, ADR-0011)`);
  }
  const raw: unknown = await response.json();
  return withExpressions(raw, modelUrl, mapping.expressions);
}
