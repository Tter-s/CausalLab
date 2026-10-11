/** 日期与显示格式化工具（UTC 输入 → 本地显示）。 */
import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";
import { enUS, zhCN } from "date-fns/locale";

/** 日期措辞跟随界面语言（由 I18nProvider 设置）。 */
let dateLocale: "zh" | "en" = "zh";
export function setDateLocale(locale: "zh" | "en") {
  dateLocale = locale;
}
function dfnsLocale() {
  return dateLocale === "en" ? enUS : zhCN;
}

export function parseDate(s: string | null | undefined): Date | null {
  if (!s) return null;
  const d = parseISO(s);
  return isValid(d) ? d : null;
}

export function fmtDateTime(s: string | null | undefined): string {
  const d = parseDate(s);
  return d ? format(d, "yyyy-MM-dd HH:mm") : "—";
}

export function fmtDate(s: string | null | undefined): string {
  const d = parseDate(s);
  return d ? format(d, "yyyy-MM-dd") : "—";
}

export function fmtRelative(s: string | null | undefined): string {
  const d = parseDate(s);
  if (!d) return "—";
  return formatDistanceToNow(d, { addSuffix: true, locale: dfnsLocale() });
}

export function fmtPercent(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

export function fmtHours(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(1)} h`;
}

export function fmtMinutes(v: number | null | undefined): string {
  if (!v) return "0 分钟";
  if (v < 60) return `${Math.round(v)} 分钟`;
  if (v < 1440) return `${(v / 60).toFixed(1)} 小时`;
  return `${(v / 1440).toFixed(1)} 天`;
}

/** ISO → <input type="datetime-local"> 值 */
export function toLocalInput(s: string | null | undefined): string {
  const d = parseDate(s);
  if (!d) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** <input type="datetime-local"> 值 → ISO（UTC, Z 后缀） */
export function fromLocalInput(s: string): string | null {
  if (!s) return null;
  const d = new Date(s);
  if (!isValid(d)) return null;
  return d.toISOString();
}

/** 供日期分组使用：本地 yyyy-MM-dd */
export function dayKey(s: string | null | undefined): string {
  const d = parseDate(s);
  return d ? format(d, "yyyy-MM-dd") : "";
}

export function dayLabel(key: string): string {
  const d = parseDate(key);
  if (!d) return key;
  const today = format(new Date(), "yyyy-MM-dd");
  if (key === today) return dateLocale === "en" ? "Today" : "今天";
  const yesterday = format(new Date(Date.now() - 86400000), "yyyy-MM-dd");
  if (key === yesterday) return dateLocale === "en" ? "Yesterday" : "昨天";
  return format(d, dateLocale === "en" ? "EEE, MMM d" : "M月d日 EEEE", { locale: dfnsLocale() });
}
