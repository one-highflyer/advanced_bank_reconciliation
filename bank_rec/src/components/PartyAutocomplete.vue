<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { searchParties } from "@/services/api";
import type { PartySearchResult } from "@/types/bankRec";

const props = withDefaults(
  defineProps<{
    company: string;
    partyType: string;
    modelValue: string;
    label?: string;
    placeholder?: string;
    disabled?: boolean;
  }>(),
  {
    label: "",
    placeholder: "Search parties",
    disabled: false,
  }
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

const query = ref(props.modelValue);
const results = ref<PartySearchResult[]>([]);
const loading = ref(false);
const error = ref("");
const open = ref(false);
let debounceTimer: ReturnType<typeof setTimeout> | undefined;
let blurTimer: ReturnType<typeof setTimeout> | undefined;
let requestId = 0;

function clearDebounce() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = undefined;
  }
}

function invalidateSearch() {
  clearDebounce();
  requestId += 1;
  loading.value = false;
}

async function runSearch(value: string, currentRequestId: number, validate = false) {
  loading.value = true;
  error.value = "";

  try {
    const rows = await searchParties({
      party_type: props.partyType,
      company: props.company,
      txt: value,
    });
    if (currentRequestId !== requestId) {
      return;
    }

    if (validate) {
      const exactResult = rows.find((row) => row.value === value);
      results.value = [];
      if (!exactResult) {
        query.value = "";
        emit("update:modelValue", "");
      }
      return;
    }

    results.value = rows;
    open.value = true;
  } catch (searchError) {
    if (currentRequestId !== requestId) {
      return;
    }
    results.value = [];
    error.value =
      searchError instanceof Error ? searchError.message : "Unable to search parties.";
  } finally {
    if (currentRequestId === requestId) {
      loading.value = false;
    }
  }
}

function scheduleSearch(value: string) {
  invalidateSearch();
  results.value = [];
  error.value = "";
  if (!props.company || !props.partyType) {
    open.value = false;
    return;
  }

  const currentRequestId = requestId;
  debounceTimer = setTimeout(() => {
    debounceTimer = undefined;
    void runSearch(value, currentRequestId);
  }, 250);
}

function handleInput(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  query.value = value;
  emit("update:modelValue", value);
  scheduleSearch(value);
}

function handleFocus() {
  if (blurTimer) {
    clearTimeout(blurTimer);
    blurTimer = undefined;
  }
  if (results.value.length) {
    open.value = true;
    return;
  }
  scheduleSearch(query.value);
}

function handleBlur() {
  blurTimer = setTimeout(() => {
    open.value = false;
    blurTimer = undefined;
  }, 150);
}

function selectResult(result: PartySearchResult) {
  invalidateSearch();
  query.value = result.value;
  results.value = [];
  error.value = "";
  open.value = false;
  emit("update:modelValue", result.value);
}

watch(
  () => props.modelValue,
  (value) => {
    if (value !== query.value) {
      query.value = value;
    }
  }
);

watch(
  () => [props.company, props.partyType] as const,
  ([company, partyType]) => {
    invalidateSearch();
    results.value = [];
    error.value = "";
    open.value = false;

    if (!company || !partyType) {
      query.value = "";
      if (props.modelValue) {
        emit("update:modelValue", "");
      }
      return;
    }

    const value = props.modelValue;
    if (!value) {
      query.value = "";
      return;
    }

    query.value = value;
    const currentRequestId = requestId;
    void runSearch(value, currentRequestId, true);
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  invalidateSearch();
  if (blurTimer) {
    clearTimeout(blurTimer);
  }
});
</script>

<template>
  <div class="relative min-w-0 flex-1">
    <label v-if="label" class="mb-1.5 block text-sm font-medium text-bank-ink">
      {{ label }}
    </label>
    <div class="relative">
      <input
        :value="query"
        :placeholder="placeholder"
        :disabled="disabled || !company || !partyType"
        class="h-9 w-full min-w-0 rounded-md border border-bank-line bg-white px-3 pr-9 text-sm outline-none transition placeholder:text-bank-muted focus:border-bank-accent focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-bank-muted"
        autocomplete="off"
        role="combobox"
        :aria-expanded="open && Boolean(results.length)"
        aria-autocomplete="list"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <div
        v-if="loading"
        class="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin rounded-full border-2 border-gray-300 border-t-bank-accent"
        role="status"
        aria-label="Loading parties"
      />
    </div>
    <div v-if="error" class="mt-1 text-xs text-red-600">
      {{ error }}
    </div>
    <div
      v-if="open && results.length"
      class="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-bank-line bg-white py-1 shadow-lg"
    >
      <button
        v-for="result in results"
        :key="result.value"
        type="button"
        class="block w-full px-3 py-2 text-left text-sm text-bank-ink hover:bg-bank-surface focus:bg-bank-surface focus:outline-none"
        @mousedown.prevent
        @click="selectResult(result)"
      >
        {{ result.label }}
      </button>
    </div>
  </div>
</template>
