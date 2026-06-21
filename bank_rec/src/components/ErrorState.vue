<script setup lang="ts">
import CircleAlert from "~icons/lucide/circle-alert";
import RefreshCcw from "~icons/lucide/refresh-cw";

defineProps<{
  title?: string;
  message: string;
  canRetry?: boolean;
}>();

defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div class="flex min-h-[180px] flex-col items-center justify-center gap-3 p-6 text-center">
    <CircleAlert class="h-8 w-8 text-red-600" />
    <div>
      <div class="text-base font-semibold text-bank-ink">
        {{ title || "Unable to load" }}
      </div>
      <div class="mt-1 max-w-md text-sm leading-6 text-bank-muted">
        {{ message }}
      </div>
    </div>
    <Button v-if="canRetry" variant="subtle" @click="$emit('retry')">
      <template #prefix>
        <RefreshCcw class="h-4 w-4" />
      </template>
      Retry
    </Button>
  </div>
</template>
