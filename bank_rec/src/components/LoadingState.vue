<script setup lang="ts">
defineProps<{
  label?: string;
}>();
</script>

<template>
  <div class="flex min-h-[180px] items-center justify-center p-6">
    <div class="flex items-center gap-3 text-sm text-bank-muted">
      <div
        class="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-bank-accent"
      />
      <span>{{ label || "Loading" }}</span>
    </div>
  </div>
</template>
