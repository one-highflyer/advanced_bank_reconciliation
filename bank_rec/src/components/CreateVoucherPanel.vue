<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type {
  AccountingDimension,
  BankTransaction,
  CreateDefaultsResponse,
  CreateVoucherPayload,
  DimensionOption,
} from "@/types/bankRec";
import EmptyState from "@/components/EmptyState.vue";
import ErrorState from "@/components/ErrorState.vue";
import LoadingState from "@/components/LoadingState.vue";
import ExternalLink from "~icons/lucide/external-link";
import Save from "~icons/lucide/save";

const props = defineProps<{
  transaction?: BankTransaction;
  defaults: CreateDefaultsResponse | null;
  loading?: boolean;
  creating?: boolean;
  drafting?: boolean;
  error?: string;
  createError?: string;
  draftError?: string;
  draftUrl?: string;
}>();

const emit = defineEmits<{
  create: [payload: CreateVoucherPayload];
  draft: [payload: CreateVoucherPayload];
  refresh: [];
}>();

const account = ref("");
const partyType = ref("");
const party = ref("");
const modeOfPayment = ref("");
const postingDate = ref("");
const referenceDate = ref("");
const referenceNumber = ref("");
const costCenter = ref("");
const project = ref("");
const dimensionValues = ref<Record<string, string>>({});
const saveAsRule = ref(false);
const ruleTitle = ref("");
const validationError = ref("");

const partyTypeOptions = [
  { label: "Not set", value: "" },
  { label: "Customer", value: "Customer" },
  { label: "Supplier", value: "Supplier" },
  { label: "Employee", value: "Employee" },
];

const accountOption = computed(() =>
  props.defaults?.options.accounts.find((row) => row.name === account.value)
);
const accountingDimensions = computed(
  () => props.defaults?.options.accounting_dimensions || []
);
const dimensionOptions = computed(
  () => props.defaults?.options.dimension_options || {}
);
const selectedAccountIsProfitAndLoss = computed(() =>
  ["Income", "Expense"].includes(accountOption.value?.root_type || "")
);

const isPaymentEntryPath = computed(() => !account.value && partyType.value && party.value);
const contactLabel = computed(() =>
  props.transaction?.direction === "withdrawal" ? "Supplier" : "Customer"
);
const accountLabel = computed(() =>
  props.transaction?.direction === "withdrawal" ? "Expense account" : "Income account"
);

function payload(): CreateVoucherPayload {
  const dimensions = getDimensionPayload();
  return {
    account: account.value,
    party_type: partyType.value,
    party: party.value,
    mode_of_payment: modeOfPayment.value,
    posting_date: postingDate.value,
    reference_date: referenceDate.value,
    reference_number: referenceNumber.value,
    cost_center: costCenter.value,
    project: project.value,
    dimensions,
    save_as_rule: saveAsRule.value,
    rule_title: ruleTitle.value,
  };
}

function getDimensionPayload() {
  const dimensions = Object.fromEntries(
    Object.entries(dimensionValues.value).filter(([, value]) => Boolean(value))
  );
  return Object.keys(dimensions).length ? dimensions : undefined;
}

function defaultDimensionValues(dimensions: AccountingDimension[]) {
  return Object.fromEntries(
    dimensions.map((dimension) => [dimension.fieldname, dimension.default_value || ""])
  );
}

function dimensionLabel(dimension: AccountingDimension) {
  return dimension.label || dimension.fieldname;
}

function dimensionDatalistId(dimension: AccountingDimension) {
  return `bank-rec-create-dimension-${dimension.fieldname}`;
}

function dimensionOptionLabel(option: DimensionOption) {
  const displayValue = Object.entries(option).find(
    ([key, value]) => key !== "name" && typeof value === "string" && value
  )?.[1];
  return typeof displayValue === "string" ? displayValue : option.name;
}

function isDimensionRequired(dimension: AccountingDimension) {
  return Boolean(
    dimension.mandatory_for_bs ||
      (selectedAccountIsProfitAndLoss.value && dimension.mandatory_for_pl)
  );
}

function validate() {
  validationError.value = "";
  if (!account.value && (!partyType.value || !party.value)) {
    validationError.value = "Choose an account or contact before creating a voucher.";
    return false;
  }
  if (
    accountOption.value?.account_type &&
    ["Receivable", "Payable"].includes(accountOption.value.account_type) &&
    (!partyType.value || !party.value)
  ) {
    validationError.value = "Contact is required for receivable or payable accounts.";
    return false;
  }
  if (saveAsRule.value && !ruleTitle.value) {
    validationError.value = "Rule title is required when saving a rule.";
    return false;
  }
  const missingDimension = accountingDimensions.value.find(
    (dimension) => isDimensionRequired(dimension) && !dimensionValues.value[dimension.fieldname]
  );
  if (missingDimension) {
    validationError.value = `${dimensionLabel(missingDimension)} is required.`;
    return false;
  }
  return true;
}

function create() {
  if (validate()) {
    emit("create", payload());
  }
}

function draft() {
  if (validate()) {
    emit("draft", payload());
  }
}

watch(
  () => props.defaults?.transaction.name,
  () => {
    account.value = "";
    partyType.value = props.defaults?.defaults.party_type || "";
    party.value = props.defaults?.defaults.party || "";
    modeOfPayment.value = "";
    postingDate.value = props.defaults?.defaults.posting_date || "";
    referenceDate.value = props.defaults?.defaults.reference_date || "";
    referenceNumber.value = props.defaults?.defaults.reference_number || "";
    costCenter.value = "";
    project.value = "";
    dimensionValues.value = defaultDimensionValues(
      props.defaults?.options.accounting_dimensions || []
    );
    saveAsRule.value = false;
    ruleTitle.value = "";
    validationError.value = "";
  },
  { immediate: true }
);
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex items-center justify-between gap-3 border-b border-bank-line px-4 py-3">
      <div>
        <div class="text-base font-semibold text-bank-ink">Create</div>
        <div class="text-sm text-bank-muted">
          {{ isPaymentEntryPath ? "Payment Entry" : "Journal Entry" }}
        </div>
      </div>
      <Button variant="subtle" :loading="loading" @click="$emit('refresh')">
        Refresh
      </Button>
    </div>

    <LoadingState v-if="loading" label="Loading create form" />
    <ErrorState
      v-else-if="error"
      :message="error"
      can-retry
      @retry="$emit('refresh')"
    />
    <EmptyState
      v-else-if="!transaction || !defaults"
      title="No transaction selected"
      detail="Select a bank transaction from the list."
    />

    <form v-else class="bank-rec-scrollbar flex min-h-0 flex-1 flex-col overflow-y-auto" @submit.prevent="create">
      <div class="grid gap-4 p-4 md:grid-cols-2">
        <div class="md:col-span-2">
          <FormControl
            v-model="account"
            :label="accountLabel"
            variant="outline"
            size="md"
            list="bank-rec-create-accounts"
          />
          <datalist id="bank-rec-create-accounts">
            <option
              v-for="row in defaults.options.accounts"
              :key="row.name"
              :value="row.name"
            >
              {{ row.account_name || row.name }}
            </option>
          </datalist>
        </div>

        <FormControl
          v-model="partyType"
          type="select"
          label="Contact type"
          variant="outline"
          size="md"
          :options="partyTypeOptions"
        />

        <FormControl
          v-model="party"
          :label="contactLabel"
          variant="outline"
          size="md"
        />

        <div>
          <FormControl
            v-model="modeOfPayment"
            label="Mode of payment"
            variant="outline"
            size="md"
            list="bank-rec-create-modes"
          />
          <datalist id="bank-rec-create-modes">
            <option
              v-for="row in defaults.options.mode_of_payments"
              :key="row.name"
              :value="row.name"
            />
          </datalist>
        </div>

        <FormControl
          v-model="postingDate"
          class="tabular-nums"
          type="date"
          label="Posting date"
          variant="outline"
          size="md"
        />

        <FormControl
          v-model="referenceDate"
          class="tabular-nums"
          type="date"
          label="Reference date"
          variant="outline"
          size="md"
        />

        <FormControl
          v-model="referenceNumber"
          label="Reference"
          variant="outline"
          size="md"
        />

        <div>
          <FormControl
            v-model="costCenter"
            label="Cost center"
            variant="outline"
            size="md"
            list="bank-rec-create-cost-centers"
          />
          <datalist id="bank-rec-create-cost-centers">
            <option
              v-for="row in defaults.options.cost_centers"
              :key="row.name"
              :value="row.name"
            >
              {{ row.cost_center_name || row.name }}
            </option>
          </datalist>
        </div>

        <div>
          <FormControl
            v-model="project"
            label="Project"
            variant="outline"
            size="md"
            list="bank-rec-create-projects"
          />
          <datalist id="bank-rec-create-projects">
            <option
              v-for="row in defaults.options.projects"
              :key="row.name"
              :value="row.name"
            >
              {{ row.project_name || row.name }}
            </option>
          </datalist>
        </div>

        <div v-for="dimension in accountingDimensions" :key="dimension.fieldname">
          <FormControl
            v-model="dimensionValues[dimension.fieldname]"
            :label="`${dimensionLabel(dimension)}${isDimensionRequired(dimension) ? ' *' : ''}`"
            variant="outline"
            size="md"
            :list="dimensionDatalistId(dimension)"
          />
          <datalist :id="dimensionDatalistId(dimension)">
            <option
              v-for="option in dimensionOptions[dimension.fieldname] || []"
              :key="option.name"
              :value="option.name"
            >
              {{ dimensionOptionLabel(option) }}
            </option>
          </datalist>
        </div>

        <FormControl
          v-model="saveAsRule"
          class="md:col-span-2"
          type="checkbox"
          label="Save as rule"
        />

        <FormControl
          v-if="saveAsRule"
          v-model="ruleTitle"
          class="md:col-span-2"
          label="Rule title"
          variant="outline"
          size="md"
        />
      </div>

      <div class="mt-auto border-t border-bank-line bg-gray-50 px-4 py-3">
        <ErrorState
          v-if="validationError || createError || draftError"
          title="Unable to create"
          :message="validationError || createError || draftError || ''"
        />
        <a
          v-if="draftUrl"
          class="mb-3 inline-flex items-center gap-2 text-sm font-medium text-bank-accent"
          :href="draftUrl"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLink class="h-4 w-4" />
          Open draft in Desk
        </a>
        <div class="flex flex-col gap-2 md:flex-row md:justify-end">
          <Button variant="subtle" :loading="drafting" @click="draft">
            <template #prefix>
              <ExternalLink class="h-4 w-4" />
            </template>
            Edit in Full Page
          </Button>
          <Button theme="blue" variant="solid" type="submit" :loading="creating">
            <template #prefix>
              <Save class="h-4 w-4" />
            </template>
            Create and Reconcile
          </Button>
        </div>
      </div>
    </form>
  </div>
</template>
