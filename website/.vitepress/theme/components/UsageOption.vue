<script setup lang="ts">
defineProps<{
  title: string;
  note?: string;
  alt?: boolean;
}>();
</script>

<template>
  <div class="usage-option" :class="{ 'usage-option--alt': alt }">
    <h3>{{ title }}</h3>
    <slot />
    <p v-if="note" class="usage-option__note">{{ note }}</p>
  </div>
</template>
