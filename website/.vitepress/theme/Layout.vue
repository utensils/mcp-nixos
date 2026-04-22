<script setup lang="ts">
import DefaultTheme from 'vitepress/theme';

const { Layout } = DefaultTheme;
</script>

<template>
  <Layout>
    <template #home-hero-image>
      <div class="hero-snowflake">
        <img src="/images/mcp-nixos.png" alt="MCP-NixOS logo" />
      </div>
    </template>
  </Layout>
</template>

<style scoped>
.hero-snowflake {
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-snowflake img {
  max-width: 280px;
  width: 100%;
  filter: drop-shadow(0 12px 24px rgba(28, 62, 90, 0.25));
  animation: float 6s ease-in-out infinite;
}
@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .hero-snowflake img {
    animation: none;
  }
}
</style>
