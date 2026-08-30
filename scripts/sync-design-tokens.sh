#!/usr/bin/env bash
# Propagate the shared design foundation into every app (see apps/shared/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
for app in hub-console spoke-app consumer-portal; do
  cp apps/shared/index.css "apps/$app/src/index.css"
  cp apps/shared/tailwind.config.js "apps/$app/tailwind.config.js"
  echo "synced -> apps/$app"
done
