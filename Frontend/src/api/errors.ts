import { ApiError, type ApiErrorPayload } from './types.js';

function asStringArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(item => asStringArray(item));
  if (typeof value === 'string') return [value];
  if (value == null) return [];
  return [String(value)];
}

export function flattenFieldErrors(detail: unknown): Record<string, string[]> {
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) return {};
  const output: Record<string, string[]> = {};
  for (const [field, value] of Object.entries(detail as Record<string, unknown>)) {
    const messages = asStringArray(value);
    if (messages.length) output[field] = messages;
  }
  return output;
}

export function humanizeApiError(status: number, payload: ApiErrorPayload | null): ApiError {
  const wrapped = payload?.error;
  const detail = wrapped?.detail ?? payload?.detail ?? payload;
  const fieldErrors = flattenFieldErrors(detail);
  const firstMessage = Object.values(fieldErrors)[0]?.[0];
  const defaults: Record<number, string> = {
    400: 'اطلاعات ارسال‌شده معتبر نیست.',
    401: 'نشست شما منقضی شده است. دوباره وارد شوید.',
    403: 'برای انجام این عملیات دسترسی کافی ندارید یا حوزه انتخاب‌شده معتبر نیست.',
    404: 'داده موردنظر پیدا نشد یا خارج از حوزه دسترسی شماست.',
    409: 'این عملیات با وضعیت فعلی داده تعارض دارد.',
    429: 'تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.',
    503: 'سرویس موقتاً آماده نیست. کمی بعد دوباره تلاش کنید.',
  };
  return new ApiError({
    status,
    code: wrapped?.code ?? `http_${status}`,
    message: firstMessage ?? defaults[status] ?? 'در پردازش درخواست خطایی رخ داد.',
    detail,
    requestId: wrapped?.request_id,
    fieldErrors,
  });
}

export function networkError(error: unknown): ApiError {
  const aborted = error instanceof DOMException && error.name === 'AbortError';
  return new ApiError({
    status: 0,
    code: aborted ? 'request_cancelled' : 'network_error',
    message: aborted ? 'درخواست لغو شد.' : 'ارتباط با سرور برقرار نشد. اتصال شبکه و آدرس API را بررسی کنید.',
    detail: error instanceof Error ? error.message : error,
  });
}
