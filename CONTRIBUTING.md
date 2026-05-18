# Contributing to Open Innova Website

Thank you for your interest in contributing! This is the public repository for the Open Innova website.
We welcome contributions to the MIT-licensed `src/` directory.

## What You Can Contribute

- Bug fixes in layout, accessibility, component behavior, or build configuration
- SEO and performance improvements
- Documentation improvements (README, docs/)
- Improvements to content schemas and validation rules
- Accessibility (a11y) enhancements
- Code quality and test improvements

## What Is Out of Scope

- Brand assets (logos, images, fonts under `assets/`) — proprietary
- Marketing copy and product descriptions (under `content/`) — proprietary
- Company data (data/company.json) — private
- Modifying deployment strategy or S3 infrastructure without explicit approval

## How to Contribute

### 1. Fork & Branch

```bash
git clone https://github.com/yourusername/open-innova-website.git
cd open-innova-website
git checkout -b fix/describe-your-fix
```

Use descriptive branch names:
- `fix/nav-mobile-layout` — bug fix
- `feat/rss-feed` — new feature
- `docs/s3-deployment-guide` — documentation
- `seo/structured-data` — SEO improvement
- `a11y/alt-text-images` — accessibility

### 2. Make Changes

- Only modify files in `src/`, public config files, or docs
- Do NOT commit anything under `assets/`, `content/`, or `data/company.json`
- Follow the coding standards below
- Ensure the build succeeds: `npm run build`

### 3. Commit with Clear Messages

Format: `<type>: <short description>`

Examples:
```
fix: nav layout broken on mobile screens
feat: add RSS feed integration
docs: update deployment checklist
seo: add JSON-LD schema to product pages
a11y: add alt text to hero images
```

### 4. Open a Pull Request

Include a clear description of:
- What problem does this solve?
- How does it solve it?
- Any testing done?

Example:
```
## Description
Fixes mobile navigation layout issue where hamburger menu overlaps logo.

## Type of Change
- [x] Bug fix
- [ ] New feature
- [ ] Documentation

## Testing
Tested on iPhone 12 (375px width) and iPad (768px width).
Verified nav menu opens/closes correctly and doesn't overlap content.
```

## Code Standards

### TypeScript
- Strict mode enabled (no `any` types)
- Meaningful variable and function names
- Export types for reuse

```typescript
// Good
export interface Product {
  id: string
  name: string
  description: string
  category: 'software' | 'consulting'
}

// Avoid
const p: any = { /* ... */ }
```

### HTML & Semantic Markup
- Use semantic elements: `<main>`, `<article>`, `<section>`, `<nav>`, `<header>`, `<footer>`
- Every image must have descriptive `alt` text
- Every image must have `width` and `height` attributes
- Never use `<div>` for interactive elements (use `<button>`, `<a>`)

```astro
<!-- Good -->
<img
  src="/images/founders/mario.jpg"
  alt="Mario Rossi, CEO and co-founder of Open Innova"
  width={400}
  height={400}
/>

<!-- Avoid -->
<div onclick="...">Click me</div>
<img src="image.jpg" />
```

### CSS
- Use only CSS custom properties from `src/styles/tokens.css`
- Never hard-code colors, spacing, or typography values
- Use semantic class names

```css
/* Good */
.card {
  padding: var(--space-md);
  color: var(--color-text);
  background: var(--color-surface);
}

/* Avoid */
.card {
  padding: 20px;
  color: #333;
  background: #fff;
}
```

### Components
- Keep components focused and single-responsibility
- Name clearly: `ProductCard`, `TeamMember`, not `Item` or `Component`
- If a file exceeds ~150 lines, consider splitting it

```astro
<!-- src/components/ProductCard.astro -->
<div class="product-card">
  <h3>{product.name}</h3>
  <p>{product.description}</p>
</div>

<style>
  .product-card {
    padding: var(--space-lg);
    border: 1px solid var(--color-border);
  }
</style>
```

## Pre-Commit Checklist

Before submitting your PR:

- [ ] `npm run build` succeeds with no errors or warnings
- [ ] `npm run preview` works locally
- [ ] No new console errors or warnings
- [ ] All strings are translatable (i18n key references, not hard-coded)
- [ ] Images have `alt` text, `width`, `height`
- [ ] No secrets in code (no API keys, credentials, emails)
- [ ] Semantic HTML used throughout
- [ ] CSS uses only token variables

## License

By submitting a pull request, you agree your contribution will be licensed under the
MIT License that covers the `src/` directory of this project.

## Questions?

- Open a GitHub issue for bugs or feature requests
- Email dev@openinnova.it for questions about contributing

---

Thank you for contributing to Open Innova!
