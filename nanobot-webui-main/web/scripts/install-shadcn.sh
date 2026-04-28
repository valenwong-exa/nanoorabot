#!/usr/bin/env bash
# Install shadcn/ui components used by nanobot webui
set -e

cd "$(dirname "$0")/.."

components=(
  button
  input
  label
  textarea
  select
  switch
  badge
  card
  dialog
  alert-dialog
  dropdown-menu
  separator
  sheet
  sidebar
  table
  tabs
  tooltip
  scroll-area
  skeleton
  avatar
  collapsible
)

echo "Installing all shadcn/ui components..."
bunx shadcn@latest add "${components[@]}" --yes

echo "All shadcn/ui components installed."
