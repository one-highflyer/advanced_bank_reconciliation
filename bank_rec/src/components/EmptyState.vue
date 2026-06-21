<script setup lang="ts">
defineProps<{
  title: string;
  detail?: string;
}>();
</script>

<template>
  <div class="flex min-h-[180px] flex-col items-center justify-center gap-2 p-6 text-center">
    <div class="text-base font-semibold text-bank-ink">{{ title }}</div>
    <div v-if="detail" class="max-w-md text-sm leading-6 text-bank-muted">
      {{ detail }}
    </div>
  </div>
</template>
