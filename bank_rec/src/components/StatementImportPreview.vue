<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type {
  StatementPreview,
  StatementPreviewRow,
} from "@/types/statementImport";
import {
  filterImportRows,
  selectedImportRows,
  selectVisibleRows,
} from "@/utils/statementImport";
import { formatDate, formatMoney } from "@/utils/format";
import Search from "~icons/lucide/search";
import TriangleAlert from "~icons/lucide/triangle-alert";
import CircleX from "~icons/lucide/circle-x";
import Check from "~icons/lucide/check";

const props = defineProps<{
  preview: StatementPreview;
  selected: number[];
  busy: boolean;
}>();
const emit = defineEmits<{
  select: [indices: number[]];
  editMapping: [];
}>();
const filter = ref("all");
const search = ref("");
const additional = ref(false);
const page = ref(1);
const pageSize = ref(25);
const filtered = computed(() =>
  filterImportRows(props.preview.rows, filter.value, search.value)
);
const totalPages = computed(() =>
  Math.max(1, Math.ceil(filtered.value.length / pageSize.value))
);
const visible = computed(() =>
  filtered.value.slice(
    (page.value - 1) * pageSize.value,
    page.value * pageSize.value
  )
);
const chosen = computed(() =>
  selectedImportRows(props.preview.rows, props.selected)
);
const totals = computed(() =>
  chosen.value.reduce(
    (total, row) => ({
      deposit: total.deposit + row.deposit,
      withdrawal: total.withdrawal + row.withdrawal,
    }),
    { deposit: 0, withdrawal: 0 }
  )
);
const selectable = computed(() =>
  visible.value.filter((row) => !row.errors.length)
);
const allPageSelected = computed(
  () =>
    selectable.value.length > 0 &&
    selectable.value.every((row) => props.selected.includes(row.index))
);
const somePageSelected = computed(
  () =>
    !allPageSelected.value &&
    selectable.value.some((row) => props.selected.includes(row.index))
);
const buttons = computed(() => [
  { label: "All " + props.preview.summary.total, value: "all" },
  { label: "Ready " + props.preview.summary.ready, value: "ready" },
  {
    label: "Possible duplicates " + props.preview.summary.possible_duplicates,
    value: "duplicates",
  },
  { label: "Errors " + props.preview.summary.errors, value: "errors" },
]);
function toggle(row: StatementPreviewRow, checked: boolean) {
  emit("select", selectVisibleRows(props.selected, [row], checked));
}
watch([filter, search, pageSize, () => props.preview], () => {
  page.value = 1;
});
watch(totalPages, (last) => {
  page.value = Math.min(page.value, last);
});
</script>

<template>
  <div>
    <div
      class="flex flex-wrap items-center justify-between gap-4 border-b border-bank-line px-4 py-4 md:px-5"
    >
      <div class="flex flex-wrap gap-x-7 gap-y-3 text-sm">
        <div>
          <div class="text-xs text-bank-muted">Selected</div>
          <div
            class="mt-1 font-medium tabular-nums text-bank-ink"
            aria-live="polite"
          >
            {{ chosen.length }} of {{ preview.summary.total }} transactions
          </div>
        </div>
        <div>
          <div class="text-xs text-bank-muted">
            Money in · {{ preview.currency }}
          </div>
          <div class="mt-1 font-medium tabular-nums text-bank-success">
            {{
              formatMoney(
                totals.deposit,
                preview.currency,
                preview.amount_precision.deposit
              )
            }}
          </div>
        </div>
        <div>
          <div class="text-xs text-bank-muted">
            Money out · {{ preview.currency }}
          </div>
          <div class="mt-1 font-medium tabular-nums text-bank-ink">
            {{
              formatMoney(
                totals.withdrawal,
                preview.currency,
                preview.amount_precision.withdrawal
              )
            }}
          </div>
        </div>
      </div>
      <Button variant="ghost" :disabled="busy" @click="emit('editMapping')"
        >Edit mapping</Button
      >
    </div>

    <div class="px-4 pt-4 md:px-5">
      <div
        v-if="preview.summary.errors"
        class="flex items-start gap-2 rounded-md bg-surface-red-2 p-3 text-sm text-ink-red-4"
        role="alert"
      >
        <CircleX class="mt-0.5 h-4 w-4 shrink-0" />
        <span
          >{{ preview.summary.errors }}
          {{ preview.summary.errors === 1 ? "row has" : "rows have" }} errors.
          Check the source row numbers below, then replace the file before
          import.</span
        >
      </div>
      <div
        v-else-if="preview.summary.possible_duplicates"
        class="flex items-start gap-2 rounded-md bg-surface-amber-2 p-3 text-sm text-ink-amber-3"
      >
        <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />
        <span
          >Possible duplicates start unselected. Select these rows only if you
          want to import them again.</span
        >
      </div>
      <div
        v-else
        class="flex items-start gap-2 rounded-md bg-bank-accent-soft p-3 text-sm text-bank-accent"
      >
        <Check class="mt-0.5 h-4 w-4 shrink-0" />
        <span>All rows are ready. No possible duplicates were found.</span>
      </div>
      <p class="mt-2 text-xs text-bank-muted">
        These are the final amounts that will be imported.
      </p>
    </div>

    <div
      class="flex flex-wrap items-center justify-between gap-3 border-b border-bank-line px-4 py-3 md:px-5"
    >
      <div class="max-w-full overflow-x-auto">
        <TabButtons v-model="filter" :options="buttons" />
      </div>
      <div class="flex w-full min-w-0 flex-wrap items-center gap-3 sm:w-auto">
        <label class="flex items-center gap-2 text-xs text-bank-muted">
          <input
            v-model="additional"
            type="checkbox"
            class="h-4 w-4 rounded accent-[var(--nexwave-primary)]"
          />
          Additional fields
        </label>
        <div class="relative w-full min-w-0 sm:w-60">
          <Search
            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bank-muted"
          />
          <input
            v-model="search"
            type="search"
            aria-label="Search preview rows"
            placeholder="Search description or reference"
            class="h-9 w-full min-w-0 rounded-md border border-bank-line bg-bank-panel pl-9 pr-3 text-sm text-bank-ink focus:border-bank-accent focus:ring-2 focus:ring-bank-accent-soft"
          />
        </div>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table
        class="w-full divide-y divide-bank-line text-left text-sm"
        :class="additional ? 'min-w-[1250px]' : 'min-w-[900px]'"
        aria-label="Transactions to import"
      >
        <thead
          class="bg-bank-muted-surface text-xs font-medium text-bank-muted"
        >
          <tr>
            <th class="w-10 px-4 py-3">
              <input
                type="checkbox"
                aria-label="Select all rows on this page"
                class="h-4 w-4 rounded accent-[var(--nexwave-primary)]"
                :checked="allPageSelected"
                :indeterminate="somePageSelected"
                :disabled="busy || !selectable.length"
                @change="
                  emit(
                    'select',
                    selectVisibleRows(
                      selected,
                      visible,
                      ($event.target as HTMLInputElement).checked
                    )
                  )
                "
              />
            </th>
            <th class="px-3 py-3">Row</th>
            <th class="whitespace-nowrap px-3 py-3">Date</th>
            <th class="px-3 py-3">Description</th>
            <th class="px-3 py-3">Reference</th>
            <template v-if="additional">
              <th class="px-3 py-3">Particulars</th>
              <th class="px-3 py-3">Code</th>
              <th class="px-3 py-3">Other party</th>
            </template>
            <th class="whitespace-nowrap px-3 py-3 text-right">Money in</th>
            <th class="whitespace-nowrap px-3 py-3 text-right">Money out</th>
            <th class="px-3 py-3">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-bank-line text-bank-ink">
          <tr
            v-for="row in visible"
            :key="row.index"
            :class="selected.includes(row.index) ? 'bg-bank-accent-soft' : ''"
          >
            <td class="px-4 py-3 align-top">
              <input
                type="checkbox"
                class="h-4 w-4 rounded accent-[var(--nexwave-primary)]"
                :aria-label="'Select source row ' + row.source_row"
                :checked="selected.includes(row.index)"
                :disabled="busy || row.errors.length > 0"
                @change="
                  toggle(row, ($event.target as HTMLInputElement).checked)
                "
              />
            </td>
            <td class="px-3 py-3 align-top tabular-nums text-bank-muted">
              {{ row.source_row }}
            </td>
            <td class="whitespace-nowrap px-3 py-3 align-top tabular-nums">
              {{
                row.date ? formatDate(row.date) : row.raw_date || "Invalid date"
              }}
            </td>
            <td
              class="min-w-[160px] max-w-[260px] break-words px-3 py-3 align-top"
            >
              {{ row.description || "No description" }}
              <div v-if="row.errors.length" class="mt-1 text-xs text-ink-red-4">
                {{ row.errors.join(" ") }}
              </div>
            </td>
            <td class="max-w-[180px] break-words px-3 py-3 align-top">
              {{ row.reference_number }}
            </td>
            <template v-if="additional">
              <td class="max-w-[200px] break-words px-3 py-3 align-top">
                {{ row.custom_particulars }}
              </td>
              <td class="px-3 py-3 align-top">{{ row.custom_code }}</td>
              <td class="max-w-[200px] break-words px-3 py-3 align-top">
                {{ row.bank_party_name }}
              </td>
            </template>
            <td
              class="whitespace-nowrap px-3 py-3 text-right align-top tabular-nums text-bank-success"
            >
              {{
                row.deposit
                  ? formatMoney(
                      row.deposit,
                      undefined,
                      preview.amount_precision.deposit
                    )
                  : ""
              }}
            </td>
            <td
              class="whitespace-nowrap px-3 py-3 text-right align-top tabular-nums"
            >
              {{
                row.withdrawal
                  ? formatMoney(
                      row.withdrawal,
                      undefined,
                      preview.amount_precision.withdrawal
                    )
                  : ""
              }}
            </td>
            <td class="px-3 py-3 align-top">
              <span
                class="inline-block whitespace-nowrap rounded px-2 py-1 text-xs font-medium"
                :class="
                  row.errors.length
                    ? 'bg-surface-red-2 text-ink-red-4'
                    : row.is_duplicate
                    ? 'bg-surface-amber-2 text-ink-amber-3'
                    : 'bg-surface-green-2 text-ink-green-3'
                "
                >{{
                  row.errors.length
                    ? "Invalid row"
                    : row.is_duplicate
                    ? "Possible duplicate"
                    : "Ready"
                }}</span
              >
            </td>
          </tr>
          <tr v-if="!visible.length">
            <td
              :colspan="additional ? 11 : 8"
              class="p-8 text-center text-bank-muted"
            >
              No rows match this view.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      class="flex flex-wrap items-center justify-between gap-3 border-t border-bank-line px-4 py-3 text-xs text-bank-muted md:px-5"
    >
      <span
        >{{ filtered.length ? (page - 1) * pageSize + 1 : 0 }}-{{
          Math.min(page * pageSize, filtered.length)
        }}
        of {{ filtered.length }} rows</span
      >
      <div class="flex items-center gap-2">
        <label class="flex items-center gap-2">
          Rows
          <select
            v-model.number="pageSize"
            class="rounded-md border border-bank-line bg-bank-panel px-2 py-1 text-bank-ink"
            aria-label="Rows per page"
          >
            <option :value="25">25</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
        </label>
        <Button variant="subtle" :disabled="page <= 1" @click="page--"
          >Previous</Button
        >
        <span class="tabular-nums">{{ page }} / {{ totalPages }}</span>
        <Button variant="subtle" :disabled="page >= totalPages" @click="page++"
          >Next</Button
        >
      </div>
    </div>
  </div>
</template>
