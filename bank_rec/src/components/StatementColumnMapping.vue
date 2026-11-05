<script setup lang="ts">
import { computed } from "vue";
import type {
  ImportContext,
  ImportMapping,
  PreparedStatement,
} from "@/types/statementImport";
import { dateFormats, hasSavedBankMapping } from "@/utils/statementImport";
import Check from "~icons/lucide/check";
import Info from "~icons/lucide/info";
import TriangleAlert from "~icons/lucide/triangle-alert";

const props = defineProps<{
  mapping: ImportMapping;
  prepared: PreparedStatement;
  context: ImportContext;
  busy: boolean;
}>();
const emit = defineEmits<{ update: [values: Partial<ImportMapping>] }>();
const columns = computed(() => [
  { label: "Select a column", value: "" },
  ...props.prepared.headers.map((header) => ({ label: header, value: header })),
]);
const optionalColumns = computed(() => [
  { label: "Not mapped", value: "" },
  ...props.prepared.headers.map((header) => ({ label: header, value: header })),
]);
const commonFields = [
  { key: "description_select", label: "Description *" },
  { key: "reference_number_select", label: "Reference number *" },
];
const additionalFields = [
  { key: "particulars_select", label: "Particulars" },
  { key: "code_select", label: "Code" },
  { key: "other_party_select", label: "Other party" },
];
function update(key: string, value: unknown) {
  emit("update", { [key]: String(value || "") });
}
</script>

<template>
  <div
    class="grid gap-6 p-4 md:p-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]"
  >
    <div class="min-w-0">
      <div
        v-if="prepared.stale_mappings.length"
        class="mb-4 flex items-start gap-2 rounded-md bg-surface-amber-2 p-3 text-sm text-ink-amber-3"
        role="status"
      >
        <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <div class="font-medium">Check the saved mapping</div>
          <div class="mt-1">
            Columns changed or are missing:
            {{ prepared.stale_mappings.join(", ") }}. Select the correct columns
            below.
          </div>
        </div>
      </div>
      <div
        v-else-if="hasSavedBankMapping(context.bank_mapping)"
        class="mb-4 flex items-start gap-2 rounded-md bg-bank-accent-soft p-3 text-sm text-bank-accent"
      >
        <Check class="mt-0.5 h-4 w-4 shrink-0" />
        <span
          >Saved mapping loaded for {{ context.bank }}. Check it against this
          file.</span
        >
      </div>
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormControl
          type="select"
          label="Date column *"
          variant="outline"
          size="md"
          :options="columns"
          :model-value="mapping.date_select"
          :disabled="busy"
          @update:model-value="update('date_select', $event)"
        />
        <FormControl
          type="select"
          label="Date format *"
          variant="outline"
          size="md"
          :options="dateFormats"
          :model-value="mapping.date_format"
          :disabled="busy"
          @update:model-value="update('date_format', $event)"
        />
        <FormControl
          v-for="field in commonFields"
          :key="field.key"
          type="select"
          variant="outline"
          size="md"
          :label="field.label"
          :options="columns"
          :model-value="mapping[field.key]"
          :disabled="busy"
          @update:model-value="update(field.key, $event)"
        />
        <FormControl
          class="sm:col-span-2"
          type="select"
          label="Amount layout"
          variant="outline"
          size="md"
          :options="[
            { label: 'Single amount column', value: 'single' },
            {
              label: 'Separate deposit / withdrawal columns',
              value: 'separate',
            },
          ]"
          :model-value="mapping.same_amount_field ? 'single' : 'separate'"
          :disabled="busy"
          @update:model-value="
            emit('update', { same_amount_field: $event === 'single' })
          "
        />
        <template v-if="mapping.same_amount_field">
          <FormControl
            type="select"
            label="Amount column *"
            variant="outline"
            size="md"
            :options="columns"
            :model-value="mapping.amount_select"
            :disabled="busy"
            @update:model-value="update('amount_select', $event)"
          />
          <FormControl
            type="select"
            label="Positive values mean *"
            variant="outline"
            size="md"
            :options="[
              { label: 'Deposit (money in)', value: 'Deposit' },
              { label: 'Withdrawal (money out)', value: 'Withdrawal' },
            ]"
            :model-value="mapping.positive_field"
            :disabled="busy"
            @update:model-value="update('positive_field', $event)"
          />
          <p class="text-xs text-bank-muted sm:col-span-2">
            Check the direction for this file. Negative values use the opposite
            direction.
          </p>
        </template>
        <template v-else>
          <FormControl
            type="select"
            label="Deposit column *"
            variant="outline"
            size="md"
            :options="columns"
            :model-value="mapping.deposit_select"
            :disabled="busy"
            @update:model-value="update('deposit_select', $event)"
          />
          <FormControl
            type="select"
            label="Withdrawal column *"
            variant="outline"
            size="md"
            :options="columns"
            :model-value="mapping.withdrawal_select"
            :disabled="busy"
            @update:model-value="update('withdrawal_select', $event)"
          />
        </template>
      </div>

      <details class="mt-5 border-t border-bank-line pt-3">
        <summary class="cursor-pointer text-sm font-medium text-bank-accent">
          Additional fields
        </summary>
        <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <FormControl
            v-for="field in additionalFields"
            :key="field.key"
            type="select"
            variant="outline"
            size="md"
            :label="field.label"
            :options="optionalColumns"
            :model-value="mapping[field.key]"
            :disabled="busy"
            @update:model-value="update(field.key, $event)"
          />
        </div>
      </details>

      <label class="mt-5 flex items-start gap-2 text-sm text-bank-ink">
        <input
          type="checkbox"
          class="mt-0.5 h-4 w-4 shrink-0 rounded border-bank-line accent-[var(--nexwave-primary)]"
          :checked="mapping.save_mapping_for_future_use"
          :disabled="busy || !context.bank || !context.can_save_mapping"
          @change="
            emit('update', {
              save_mapping_for_future_use: ($event.target as HTMLInputElement)
                .checked,
            })
          "
        />
        <span>
          Save this mapping{{ context.bank ? " for " + context.bank : "" }}
          <span class="mt-1 block text-xs text-bank-muted">
            <template v-if="!context.bank"
              >Link this account to a bank to save a mapping.</template
            >
            <template v-else-if="!context.can_save_mapping">
              You do not have permission to update this bank's saved mapping.
            </template>
            <template v-else>
              Used by other accounts linked to this bank. Check the amount
              direction on each import.
            </template>
          </span>
        </span>
      </label>
    </div>

    <aside
      class="min-w-0 border-t border-bank-line pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0"
    >
      <div class="text-sm font-semibold text-bank-ink">File preview</div>
      <p class="mb-3 mt-1 text-xs text-bank-muted">
        First {{ prepared.preview_rows.length }} rows · original file values
      </p>
      <div class="overflow-x-auto rounded-md border border-bank-line">
        <table class="min-w-full text-left text-xs">
          <thead class="bg-bank-muted-surface text-bank-muted">
            <tr>
              <th
                v-for="(header, index) in prepared.headers"
                :key="index"
                class="whitespace-nowrap px-3 py-2.5 font-medium"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-bank-line text-bank-ink">
            <tr v-for="(row, index) in prepared.preview_rows" :key="index">
              <td
                v-for="(_, column) in prepared.headers"
                :key="column"
                class="whitespace-nowrap px-3 py-3 tabular-nums"
              >
                {{ row[column] ?? "" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="mt-3 text-xs text-bank-muted">
        Use an explicit date format when the file's dates are ambiguous.
      </p>
      <div
        v-if="context.is_credit_card"
        class="mt-5 flex items-start gap-2 rounded-md bg-bank-accent-soft p-3 text-sm text-bank-accent"
      >
        <Info class="mt-0.5 h-4 w-4 shrink-0" />
        <span
          >Credit-card directions are adjusted automatically. Check the final
          amounts in the next step.</span
        >
      </div>
    </aside>
  </div>
</template>
