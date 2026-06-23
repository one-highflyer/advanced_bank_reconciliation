<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type {
  BankTransaction,
  MatchCandidate,
  MatchVoucherSelection,
} from "@/types/bankRec";
import { deskRoute } from "@/utils/desk";
import { formatDate, formatMoney } from "@/utils/format";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import ExternalLink from "~icons/lucide/external-link";
import RefreshCcw from "~icons/lucide/refresh-cw";

const props = defineProps<{
  transaction?: BankTransaction;
  candidates: MatchCandidate[];
  loading?: boolean;
  submitting?: boolean;
  error?: string;
  submitError?: string;
  currency?: string;
}>();

const emit = defineEmits<{
  refresh: [];
  submit: [vouchers: MatchVoucherSelection[]];
}>();

const selectedKeys = ref<string[]>([]);
const amounts = ref<Record<string, number | string | null>>({});

const selectedCandidates = computed(() =>
  props.candidates.filter((candidate) => selectedKeys.value.includes(candidate.key))
);

function allocationAmount(candidate: MatchCandidate) {
  const value = amounts.value[candidate.key] ?? Math.abs(candidate.amount);
  return Number(value);
}

const selectedTotal = computed(() =>
  selectedCandidates.value.reduce((total, candidate) => {
    const amount = allocationAmount(candidate);
    return total + (Number.isFinite(amount) ? Math.abs(amount) : 0);
  }, 0)
);

const invalidSelectedCandidates = computed(() =>
  selectedCandidates.value.filter((candidate) => {
    const amount = allocationAmount(candidate);
    return !Number.isFinite(amount) || amount <= 0;
  })
);

const canSubmit = computed(
  () => Boolean(selectedCandidates.value.length) && !invalidSelectedCandidates.value.length
);

function confidenceTheme(confidence: MatchCandidate["confidence"]) {
  if (confidence === "high") {
    return "green";
  }
  if (confidence === "medium") {
    return "orange";
  }
  return "gray";
}

function toggleCandidate(candidate: MatchCandidate, checked: boolean) {
  if (checked && !selectedKeys.value.includes(candidate.key)) {
    selectedKeys.value = [...selectedKeys.value, candidate.key];
  }
  if (!checked) {
    selectedKeys.value = selectedKeys.value.filter((key) => key !== candidate.key);
  }
}

function voucherUrl(candidate: MatchCandidate) {
  return deskRoute(candidate.voucher_type, candidate.voucher_name);
}

function submit() {
  if (!canSubmit.value || props.submitting) {
    return;
  }

  const vouchers = selectedCandidates.value.map((candidate) => ({
    voucher_type: candidate.voucher_type,
    voucher_name: candidate.voucher_name,
    amount: allocationAmount(candidate),
  }));
  emit("submit", vouchers);
}

watch(
  () => props.candidates,
  (candidates) => {
    amounts.value = Object.fromEntries(
      candidates.map((candidate) => [candidate.key, Math.abs(candidate.amount)])
    );

    const topRank = Math.max(0, ...candidates.map((candidate) => candidate.rank));
    const topCandidates = candidates.filter(
      (candidate) => candidate.rank === topRank && candidate.confidence === "high"
    );
    selectedKeys.value = topCandidates.length === 1 ? [topCandidates[0].key] : [];
  },
  { immediate: true }
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex items-center justify-between gap-3 border-b border-bank-line px-4 py-3">
      <div>
        <div class="text-base font-semibold text-bank-ink">Match</div>
        <div class="text-sm text-bank-muted">
          {{ candidates.length }} candidates
        </div>
      </div>
      <Button variant="subtle" :loading="loading" @click="$emit('refresh')">
        <template #prefix>
          <RefreshCcw class="h-4 w-4" />
        </template>
        Refresh
      </Button>
    </div>

    <LoadingState v-if="loading" label="Loading candidates" />
    <ErrorState
      v-else-if="error"
      :message="error"
      can-retry
      @retry="$emit('refresh')"
    />
    <EmptyState
      v-else-if="!transaction"
      title="No transaction selected"
      detail="Select a bank transaction from the list."
    />
    <EmptyState
      v-else-if="!candidates.length"
      title="No match candidates"
      detail="Use Create when no existing document matches this bank transaction."
    />

    <template v-else>
      <div class="bank-rec-scrollbar min-h-0 flex-1 overflow-auto">
        <table class="min-w-full divide-y divide-bank-line text-sm">
          <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
            <tr>
              <th class="w-10 px-4 py-3"></th>
              <th class="px-4 py-3">Document</th>
              <th class="px-4 py-3">Reference</th>
              <th class="px-4 py-3">Date</th>
              <th class="px-4 py-3 text-right">Amount</th>
              <th class="px-4 py-3 text-right">Allocate</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-bank-line bg-white">
            <tr v-for="candidate in candidates" :key="candidate.key">
              <td class="px-4 py-3 align-top">
                <input
                  class="h-4 w-4 rounded border-bank-line text-bank-accent"
                  type="checkbox"
                  :checked="selectedKeys.includes(candidate.key)"
                  @change="toggleCandidate(candidate, ($event.target as HTMLInputElement).checked)"
                />
              </td>
              <td class="max-w-[260px] px-4 py-3 align-top">
                <a
                  class="inline-flex max-w-full items-center gap-2 truncate font-medium text-bank-accent"
                  :href="voucherUrl(candidate)"
                  target="_blank"
                  rel="noreferrer"
                >
                  <span class="truncate">
                  {{ candidate.voucher_name }}
                  </span>
                  <ExternalLink class="h-3.5 w-3.5 shrink-0" />
                </a>
                <div class="mt-1 flex flex-wrap gap-1">
                  <Badge :theme="confidenceTheme(candidate.confidence)">
                    {{ candidate.confidence }}
                  </Badge>
                  <Badge
                    v-for="reason in candidate.reasons"
                    :key="reason"
                    theme="gray"
                  >
                    {{ reason }}
                  </Badge>
                </div>
                <div class="mt-1 text-xs text-bank-muted">
                  {{ candidate.voucher_type }}
                </div>
              </td>
              <td class="max-w-[180px] px-4 py-3 align-top text-bank-ink">
                <div class="truncate">{{ candidate.reference_number || "Not set" }}</div>
                <div class="truncate text-xs text-bank-muted">
                  {{ candidate.party_name || candidate.party || "No party" }}
                </div>
              </td>
              <td class="px-4 py-3 align-top text-bank-ink">
                {{ formatDate(candidate.posting_date || candidate.reference_date) }}
              </td>
              <td class="px-4 py-3 text-right align-top font-medium text-bank-ink">
                {{ formatMoney(candidate.amount, candidate.currency || currency) }}
              </td>
              <td class="px-4 py-3 text-right align-top">
                <input
                  v-model.number="amounts[candidate.key]"
                  class="h-9 w-28 rounded-md border border-bank-line px-2 text-right text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
                  type="number"
                  min="0.01"
                  step="0.01"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="border-t border-bank-line bg-gray-50 px-4 py-3">
        <ErrorState
          v-if="submitError"
          title="Unable to reconcile"
          :message="submitError"
        />
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div class="text-sm text-bank-muted">
            Selected total:
            <span class="font-semibold text-bank-ink">
              {{ formatMoney(selectedTotal, transaction.currency || currency) }}
            </span>
            <span
              v-if="invalidSelectedCandidates.length"
              class="ml-2 font-medium text-red-700"
            >
              Enter positive allocation amounts.
            </span>
          </div>
          <Button
            theme="blue"
            :disabled="!canSubmit || submitting"
            :loading="submitting"
            @click="submit"
          >
            <template #prefix>
              <CheckCircle2 class="h-4 w-4" />
            </template>
            Save and Reconcile
          </Button>
        </div>
      </div>
    </template>
  </div>
</template>
