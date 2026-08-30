#!/usr/bin/env bash
# Fail if any app's design foundation has drifted from apps/shared (run in CI).
set -euo pipefail
cd "$(dirname "$0")/.."
rc=0
for app in hub-console spoke-app consumer-portal; do
  diff -q apps/shared/index.css "apps/$app/src/index.css" >/dev/null || { echo "DRIFT: apps/$app/src/index.css differs from apps/shared/index.css"; rc=1; }
  diff -q apps/shared/tailwind.config.js "apps/$app/tailwind.config.js" >/dev/null || { echo "DRIFT: apps/$app/tailwind.config.js differs from apps/shared/tailwind.config.js"; rc=1; }
done
[ $rc -eq 0 ] && echo "design tokens in sync across all apps."
exit $rc
