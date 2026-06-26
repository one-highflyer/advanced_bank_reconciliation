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
import Check from "~icons/lucide/check";
import CheckCircle2 from "~icons/lucide/check-circle-2";
import ExternalLink from "~icons/lucide/external-link";
import RefreshCcw from "~icons/lucide/refresh-cw";
import Search from "~icons/lucide/search";

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
const search = ref("");

const selectedCandidates = computed(() =>
  props.candidates.filter((candidate) => selectedKeys.value.includes(candidate.key))
);
const filteredCandidates = computed(() => {
  const term = search.value.trim().toLowerCase();
  if (!term) {
    return props.candidates;
  }
  return props.candidates.filter((candidate) =>
    candidateSearchText(candidate).includes(term)
  );
});

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

const allocatableAmount = computed(() => {
  if (!props.transaction) {
    return 0;
  }
  const unallocated = Math.abs(Number(props.transaction.unallocated_amount || 0));
  return unallocated || Math.abs(Number(props.transaction.amount || 0));
});

const fullyAllocated = computed(
  () =>
    Boolean(selectedCandidates.value.length) &&
    allocatableAmount.value > 0 &&
    Math.abs(selectedTotal.value - allocatableAmount.value) < 0.005
);

function confidenceDotClass(confidence: MatchCandidate["confidence"]) {
  if (confidence === "high") {
    return "bg-green-500";
  }
  if (confidence === "medium") {
    return "bg-amber-500";
  }
  return "bg-bank-subtle";
}

function confidenceLabel(confidence: MatchCandidate["confidence"]) {
  if (confidence === "high") {
    return "High confidence";
  }
  if (confidence === "medium") {
    return "Medium confidence";
  }
  return "Low confidence";
}

function candidateSearchText(candidate: MatchCandidate) {
  return [
    candidate.voucher_name,
    candidate.voucher_type,
    candidate.source_type,
    candidate.reference_number,
    candidate.party_name,
    candidate.party,
    candidate.party_type,
    candidate.posting_date,
    candidate.reference_date,
    candidate.amount,
    candidate.currency,
    confidenceLabel(candidate.confidence),
    ...candidate.reasons,
  ]
    .filter((value) => value !== undefined && value !== null)
    .join(" ")
    .toLowerCase();
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
    search.value = "";
  },
  { immediate: true }
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex items-center justify-between gap-3 border-b border-bank-line px-4 py-3">
      <div>
        <div class="text-base font-semibold text-bank-ink">Match</div>
        <div class="text-sm tabular-nums text-bank-muted">
          {{ search ? `${filteredCandidates.length} of ${candidates.length}` : candidates.length }} candidates
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
      <div class="border-b border-bank-line px-4 py-3">
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bank-muted" />
          <input
            v-model="search"
            class="h-9 w-full rounded-md border border-bank-line bg-white pl-9 pr-3 text-sm outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="search"
            placeholder="Search documents, references, parties, dates, amounts"
          />
        </div>
      </div>

      <EmptyState
        v-if="!filteredCandidates.length"
        class="min-h-0 flex-1"
        title="No candidates match search"
        detail="Change the search term or refresh candidates."
      />

      <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-auto">
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
            <tr
              v-for="candidate in filteredCandidates"
              :key="candidate.key"
              :class="selectedKeys.includes(candidate.key) ? 'bg-bank-accent-50' : ''"
            >
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
                <div class="mt-1.5">
                  <span class="inline-flex items-center gap-1.5 text-xs font-semibold">
                    <span
                      class="h-2 w-2 rounded-full"
                      :class="confidenceDotClass(candidate.confidence)"
                    />
                    {{ confidenceLabel(candidate.confidence) }}
                  </span>
                </div>
                <div class="mt-1.5 flex flex-wrap gap-1">
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
              <td class="px-4 py-3 align-top tabular-nums text-bank-ink">
                {{ formatDate(candidate.posting_date || candidate.reference_date) }}
              </td>
              <td class="px-4 py-3 text-right align-top font-medium tabular-nums text-bank-ink">
                {{ formatMoney(candidate.amount, candidate.currency || currency) }}
              </td>
              <td class="px-4 py-3 text-right align-top">
                <input
                  v-model.number="amounts[candidate.key]"
                  class="h-9 w-28 rounded-md border border-bank-line px-2 text-right text-sm tabular-nums outline-none focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
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
          <div class="flex flex-wrap items-center gap-2 text-sm text-bank-muted">
            <span>
              Selected total:
              <span class="font-semibold tabular-nums text-bank-ink">
                {{ formatMoney(selectedTotal, transaction.currency || currency) }}
              </span>
            </span>
            <span
              v-if="fullyAllocated"
              class="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-700"
            >
              <Check class="h-3.5 w-3.5" />
              Fully allocated
            </span>
            <span
              v-if="invalidSelectedCandidates.length"
              class="font-medium text-red-700"
            >
              Enter positive allocation amounts.
            </span>
          </div>
          <Button
            theme="blue"
            variant="solid"
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
