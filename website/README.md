# MCP-NixOS Website

The official marketing + documentation site for the MCP-NixOS project. Built with
[VitePress](https://vitepress.dev/) and deployed automatically via CI/CD to AWS S3 and
CloudFront.

## Stack

- **[VitePress 1.x](https://vitepress.dev/)** — Vue-powered static site generator
- **Custom theme** — Default VitePress theme extended with NixOS brand colors
- **Markdown-first content** — `index.md`, `usage.md`, `about.md`
- **Static export** — Output lands in `website/out/` for S3/CloudFront hosting

## Getting Started

### Using Nix (recommended)

From the repo root, drop into the website dev shell:

```bash
nix develop .#web
```

You'll get Node.js, npm, and a `menu` printout with the common commands. Then:

```bash
npm install       # one-time, installs VitePress + deps
npm run dev       # local dev server with hot reload (http://localhost:5173)
npm run build     # static build into website/out/
npm run preview   # serve the built site locally
```

Or use the convenience helpers printed by the menu:

```bash
web-install       # npm install
web-dev           # npm run dev
web-build         # npm run build
web-preview       # npm run preview
```

### Without Nix

Any Node.js 20+ will do:

```bash
cd website
npm install
npm run dev
```

## Project Structure

```
website/
├── .vitepress/
│   ├── config.mts          # Site config: nav, sidebar, SEO, theme
│   └── theme/
│       ├── index.ts        # Theme entry — registers components + CSS
│       ├── Layout.vue      # Layout override (hero image animation)
│       ├── style.css       # NixOS palette + custom components
│       └── components/
│           ├── AuthorCard.vue
│           └── UsageOption.vue
├── index.md                # Home page
├── usage.md                # Usage / configuration reference
├── about.md                # Project overview, architecture, authors
├── public/                 # Static assets served from /
│   ├── favicon/
│   └── images/
└── package.json
```

## Design Notes

The theme uses the NixOS brand palette:

| Token | Hex | Role |
|-------|-----|------|
| `--nix-primary` | `#5277C3` | Primary blue (buttons, links, brand) |
| `--nix-secondary` | `#7EBAE4` | Secondary blue (accents) |
| `--nix-dark` | `#1C3E5A` | Dark blue (contrast, headers) |
| `--nix-light` | `#E6F0FA` | Light blue (backgrounds) |

Light and dark modes are both supported out of the box (VitePress handles the toggle).

## Deployment

The `deploy-website.yml` GitHub Actions workflow builds on push to `main` (when anything
under `website/` changes) and syncs `website/out/` to S3, then invalidates CloudFront.

## Editing Content

- Marketing copy and feature grid: `index.md` frontmatter.
- Installation options and tool reference: `usage.md`.
- Project context, architecture, and bios: `about.md`.

Keep the voice. MCP-NixOS has one.
