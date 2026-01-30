import nextConfig from "eslint-config-next";

const config = [
  {
    ignores: [".next/**", "out/**", "node_modules/**"],
  },
  ...nextConfig,
];

export default config;
