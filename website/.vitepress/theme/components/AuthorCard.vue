<script setup lang="ts">
interface Link {
  label: string;
  url: string;
}

defineProps<{
  name: string;
  role: string;
  image: string;
  links?: Link[];
}>();
</script>

<template>
  <div class="author-card">
    <div class="author-card__avatar">
      <img :src="image" :alt="name" />
    </div>
    <div class="author-card__body">
      <h3>{{ name }}</h3>
      <p class="author-card__role">{{ role }}</p>
      <slot />
      <div v-if="links && links.length" class="author-card__links">
        <a
          v-for="link in links"
          :key="link.url"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ link.label }}
        </a>
      </div>
    </div>
  </div>
</template>
