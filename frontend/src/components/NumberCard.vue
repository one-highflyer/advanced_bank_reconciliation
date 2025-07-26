<template>
  <div class="bg-white overflow-hidden shadow rounded-lg">
    <div class="p-5">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div 
            class="w-8 h-8 rounded-md flex items-center justify-center"
            :class="iconClasses"
          >
            <FeatherIcon 
              :name="iconName" 
              class="w-5 h-5"
              :class="iconColorClasses"
            />
          </div>
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">
              {{ title }}
            </dt>
            <dd class="flex items-baseline">
              <div class="text-2xl font-semibold" :class="valueColorClasses">
                {{ formattedValue }}
              </div>
              <div 
                v-if="change" 
                class="ml-2 flex items-baseline text-sm font-semibold"
                :class="changeColorClasses"
              >
                <FeatherIcon 
                  :name="changeIcon" 
                  class="w-4 h-4 mr-1"
                />
                {{ change }}
              </div>
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatCurrency } from '@/utils/currency'

// Props
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    required: true
  },
  currency: {
    type: String,
    default: 'USD'
  },
  variant: {
    type: String,
    default: 'default',
    validator: (value) => ['default', 'info', 'success', 'warning', 'danger'].includes(value)
  },
  change: {
    type: String,
    default: null
  },
  icon: {
    type: String,
    default: null
  }
})

// Computed properties
const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return formatCurrency(props.value, props.currency)
  }
  return props.value
})

const iconName = computed(() => {
  if (props.icon) return props.icon
  
  // Default icons based on variant
  const iconMap = {
    default: 'dollar-sign',
    info: 'info',
    success: 'check-circle',
    warning: 'alert-triangle',
    danger: 'x-circle'
  }
  return iconMap[props.variant] || 'dollar-sign'
})

const iconClasses = computed(() => {
  const baseClasses = 'w-8 h-8 rounded-md flex items-center justify-center'
  const variantClasses = {
    default: 'bg-gray-100',
    info: 'bg-blue-100',
    success: 'bg-green-100',
    warning: 'bg-yellow-100',
    danger: 'bg-red-100'
  }
  return `${baseClasses} ${variantClasses[props.variant]}`
})

const iconColorClasses = computed(() => {
  const colorMap = {
    default: 'text-gray-600',
    info: 'text-blue-600',
    success: 'text-green-600',
    warning: 'text-yellow-600',
    danger: 'text-red-600'
  }
  return colorMap[props.variant]
})

const valueColorClasses = computed(() => {
  const colorMap = {
    default: 'text-gray-900',
    info: 'text-blue-900',
    success: 'text-green-900',
    warning: 'text-yellow-900',
    danger: 'text-red-900'
  }
  return colorMap[props.variant]
})

const changeColorClasses = computed(() => {
  if (!props.change) return ''
  
  // Determine color based on change direction
  if (props.change.startsWith('+')) {
    return 'text-green-600'
  } else if (props.change.startsWith('-')) {
    return 'text-red-600'
  }
  return 'text-gray-600'
})

const changeIcon = computed(() => {
  if (!props.change) return ''
  
  if (props.change.startsWith('+')) {
    return 'trending-up'
  } else if (props.change.startsWith('-')) {
    return 'trending-down'
  }
  return 'minus'
})
</script> 