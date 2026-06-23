function padDatePart(value: number) {
  return String(value).padStart(2, "0");
}

function localDateIso(date: Date) {
  return [
    date.getFullYear(),
    padDatePart(date.getMonth() + 1),
    padDatePart(date.getDate()),
  ].join("-");
}

function parseDisplayDate(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  return new Date(value);
}

export function todayIso() {
  return localDateIso(new Date());
}

export function monthStartIso() {
  const now = new Date();
  return localDateIso(new Date(now.getFullYear(), now.getMonth(), 1));
}

export function formatDate(value?: string) {
  if (!value) {
    return "Not set";
  }

  const date = parseDisplayDate(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(date);
}

export function formatMoney(amount?: number | null, currency?: string) {
  const value = Number(amount || 0);

  if (currency) {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency,
      }).format(value);
    } catch {
      return `${currency} ${value.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;
    }
  }

  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function signedAmountClass(amount?: number | null) {
  const value = Number(amount || 0);
  if (value > 0) {
    return "text-green-700";
  }
  if (value < 0) {
    return "text-red-700";
  }
  return "text-gray-700";
}
