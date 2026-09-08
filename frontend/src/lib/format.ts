export function formatDateTime(
  value?: string | null
): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "medium"
    }
  ).format(
    new Date(value)
  );
}

export function formatShortDateTime(
  value?: string | null
): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    }
  ).format(
    new Date(value)
  );
}

export function formatTime(
  value?: string | null
): string {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    }
  ).format(
    new Date(value)
  );
}

export function formatPercent(
  value: number
): string {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      style: "percent",
      maximumFractionDigits: 1
    }
  ).format(value);
}

export function formatDecimal(
  value: number,
  maximumFractionDigits = 3
): string {
  return new Intl.NumberFormat(
    "pt-BR",
    {
      maximumFractionDigits
    }
  ).format(value);
}
