export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function monthStartIso() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
}

export function formatDate(value?: string) {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);
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
