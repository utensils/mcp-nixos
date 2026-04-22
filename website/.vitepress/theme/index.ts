import type { Theme } from 'vitepress';
import DefaultTheme from 'vitepress/theme';
import Layout from './Layout.vue';
import AuthorCard from './components/AuthorCard.vue';
import UsageOption from './components/UsageOption.vue';
import './style.css';

export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('AuthorCard', AuthorCard);
    app.component('UsageOption', UsageOption);
  },
} satisfies Theme;
