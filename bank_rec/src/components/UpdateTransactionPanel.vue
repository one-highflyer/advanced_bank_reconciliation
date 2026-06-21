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

const partyTypeOptions = [
  { label: "Not set", value: "" },
  { label: "Customer", value: "Customer" },
  { label: "Supplier", value: "Supplier" },
  { label: "Employee", value: "Employee" },
];

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
        <FormControl
          v-model="referenceNumber"
          class="md:col-span-2"
          label="Reference"
          variant="outline"
          size="md"
        />

        <FormControl
          v-model="partyType"
          type="select"
          label="Party type"
          variant="outline"
          size="md"
          :options="partyTypeOptions"
        />

        <FormControl
          v-model="party"
          label="Party"
          variant="outline"
          size="md"
        />
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
