<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { BankTransaction } from "@/types/bankRec";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import Save from "~icons/lucide/save";

const props = defineProps<{
  transaction?: BankTransaction;
  submitting?: boolean;
  error?: string;
}>();

const emit = defineEmits<{
  submit: [payload: { reference_number?: string; party_type?: string; party?: string }];
}>();

const referenceNumber = ref("");
const partyType = ref("");
const party = ref("");

const dirty = computed(() => {
  if (!props.transaction) {
    return false;
  }
  return (
    referenceNumber.value !== (props.transaction.reference_number || "") ||
    partyType.value !== (props.transaction.party_type || "") ||
    party.value !== (props.transaction.party || "")
  );
});

function submit() {
  emit("submit", {
    reference_number: referenceNumber.value,
    party_type: partyType.value,
    party: party.value,
  });
}

watch(
  () => props.transaction?.name,
  () => {
    referenceNumber.value = props.transaction?.reference_number || "";
    partyType.value = props.transaction?.party_type || "";
    party.value = props.transaction?.party || "";
  },
  { immediate: true }
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="border-b border-bank-line px-4 py-3">
      <div class="text-base font-semibold text-bank-ink">Update</div>
      <div class="text-sm text-bank-muted">
        {{ transaction?.name || "No transaction selected" }}
      </div>
    </div>

    <LoadingState v-if="!transaction" label="Select a transaction" />

    <form v-else class="flex flex-1 flex-col" @submit.prevent="submit">
      <div class="grid gap-4 p-4 md:grid-cols-2">
        <label class="block md:col-span-2">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Reference
          </span>
          <input
            v-model="referenceNumber"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="text"
          />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Party type
          </span>
          <select
            v-model="partyType"
            class="h-10 w-full rounded-md border border-bank-line bg-white px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
          >
            <option value="">Not set</option>
            <option value="Customer">Customer</option>
            <option value="Supplier">Supplier</option>
            <option value="Employee">Employee</option>
          </select>
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-medium uppercase tracking-wide text-bank-muted">
            Party
          </span>
          <input
            v-model="party"
            class="h-10 w-full rounded-md border border-bank-line px-3 text-sm outline-none transition focus:border-bank-accent focus:ring-2 focus:ring-blue-100"
            type="text"
          />
        </label>
      </div>

      <div class="mt-auto border-t border-bank-line bg-gray-50 px-4 py-3">
        <ErrorState
          v-if="error"
          title="Unable to update"
          :message="error"
        />
        <div class="flex justify-end">
          <Button
            theme="blue"
            type="submit"
            :disabled="!dirty"
            :loading="submitting"
          >
            <template #prefix>
              <Save class="h-4 w-4" />
            </template>
            Save
          </Button>
        </div>
      </div>
    </form>
  </div>
</template>
