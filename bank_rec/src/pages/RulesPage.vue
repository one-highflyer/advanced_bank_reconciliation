<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import BankAccountFilters from "@/components/BankAccountFilters.vue";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import { useBankRecStore } from "@/stores/bankRec";
import ExternalLink from "~icons/lucide/external-link";
import Search from "~icons/lucide/search";

const store = useBankRecStore();
const search = ref("");
const selectedBankAccount = ref("");

const filteredRules = computed(() => {
  const term = search.value.trim().toLowerCase();
  if (!term) {
    return store.rules;
  }

  return store.rules.filter((rule) =>
    [
      rule.title,
      rule.name,
      rule.entry_type,
      rule.account,
      rule.party,
      rule.company,
      rule.bank_account,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(term))
  );
});

async function loadRules() {
  await store.loadRules(selectedBankAccount.value || undefined);
}

onMounted(async () => {
  await store.initialize({});
  selectedBankAccount.value = store.selectedBankAccount;
  await loadRules();
});

watch(selectedBankAccount, loadRules);
</script>

<template>
  <div class="flex min-h-0 w-full flex-col gap-4">
    <BankAccountFilters
      :bank-accounts="store.bankAccounts"
      :selected-bank-account="selectedBankAccount"
      :from-date="store.fromDate"
      :to-date="store.toDate"
      :loading="store.loading.bankAccounts || store.loading.rules"
      @update:selected-bank-account="selectedBankAccount = $event"
      @update:from-date="store.fromDate = $event"
      @update:to-date="store.toDate = $event"
      @refresh="loadRules"
    />

    <section class="flex min-h-[620px] flex-col rounded-lg border border-bank-line bg-white shadow-sm">
      <div class="flex flex-col gap-3 border-b border-bank-line px-4 py-3 md:flex-row md:items-center md:justify-between">
        <div>
          <div class="text-base font-semibold text-bank-ink">Rules</div>
          <div class="text-sm text-bank-muted">
            {{ filteredRules.length }} visible
          </div>
        </div>
        <label class="relative block md:w-80">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bank-muted" />
          <input
            v-model="search"
            class="h-10 w-full rounded-md border border-bank-line pl-9 pr-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="search"
            placeholder="Search rules"
          />
        </label>
      </div>

      <LoadingState v-if="store.loading.rules" label="Loading rules" />
      <ErrorState
        v-else-if="store.errors.rules"
        :message="store.errors.rules"
        can-retry
        @retry="loadRules"
      />
      <EmptyState
        v-else-if="!filteredRules.length"
        title="No rules found"
        detail="Change the bank account filter or search term."
      />
      <div v-else class="bank-rec-scrollbar min-h-0 flex-1 overflow-auto">
        <table class="min-w-full divide-y divide-bank-line text-sm">
          <thead class="sticky top-0 bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-bank-muted">
            <tr>
              <th class="px-4 py-3">Rule</th>
              <th class="px-4 py-3">Entry type</th>
              <th class="px-4 py-3">Account</th>
              <th class="px-4 py-3">Party</th>
              <th class="px-4 py-3">Priority</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-bank-line bg-white">
            <tr v-for="rule in filteredRules" :key="rule.name">
              <td class="max-w-[280px] px-4 py-3">
                <div class="truncate font-medium text-bank-ink">
                  {{ rule.title || rule.name }}
                </div>
                <div class="truncate text-xs text-bank-muted">
                  {{ rule.company || "No company" }}
                </div>
              </td>
              <td class="px-4 py-3 text-bank-ink">
                {{ rule.entry_type || "Not set" }}
              </td>
              <td class="max-w-[240px] px-4 py-3">
                <div class="truncate text-bank-ink">
                  {{ rule.account || "Not set" }}
                </div>
              </td>
              <td class="max-w-[220px] px-4 py-3">
                <div class="truncate text-bank-ink">
                  {{ rule.party || rule.party_type || "Not set" }}
                </div>
              </td>
              <td class="px-4 py-3 text-bank-ink">
                {{ rule.priority ?? "Not set" }}
              </td>
              <td class="px-4 py-3">
                <Badge :theme="rule.enabled ? 'green' : 'gray'">
                  {{ rule.enabled ? "Enabled" : "Disabled" }}
                </Badge>
              </td>
              <td class="px-4 py-3 text-right">
                <a
                  class="inline-flex h-8 items-center gap-2 rounded-md border border-bank-line px-3 text-sm font-medium text-bank-ink transition hover:bg-gray-50"
                  :href="rule.desk_url"
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink class="h-4 w-4" />
                  Open
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
