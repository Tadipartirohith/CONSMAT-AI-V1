# Shared design foundation (single source of truth)

`index.css` (design tokens + Geist self-host hook + quiet-elevation utilities) and
`tailwind.config.js` (token -> CSS-variable mapping, fonts, radius scale) are the ONE
canonical copy of the Consmat design language. All three apps (hub-console, spoke-app,
consumer-portal) build in isolated Docker contexts, so they cannot import a file from
outside their own folder; instead each app keeps a generated copy.

- Edit the design language **here only**.
- Run `scripts/sync-design-tokens.sh` to propagate into every app.
- CI runs `scripts/check-design-tokens.sh` to fail the build if any app drifts.
