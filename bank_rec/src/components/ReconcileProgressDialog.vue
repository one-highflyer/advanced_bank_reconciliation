<script setup lang="ts">
defineProps<{
  open: boolean;
  title?: string;
  message?: string;
}>();
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
  >
    <div class="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
      <div class="text-base font-semibold text-bank-ink">
        {{ title || "Reconciling" }}
      </div>
      <div class="mt-2 text-sm text-bank-muted">
        {{ message || "Processing selected rows" }}
      </div>
    </div>
  </div>
</template>
