# The Project Management MVP web app

## Business Requirements

This project is building a Project Management App. Key features:
- A user can sign in
- When signed in, the user sees a Kanban board representing their project
- The Kanban board has fixed columns that can be renamed
- The cards on the Kanban board can be moved with drag and drop, and edited
- There is an AI chat feature in a sidebar; the AI is able to create / edit / move one or more cards

## Limitations

For the MVP, there will only be a user sign in (hardcoded to 'user' and 'password') but the database will support multiple users for future.

For the MVP, there will only be 1 Kanban board per signed in user.

For the MVP, this will run locally (in a docker container)

## Technical Decisions

- NextJS frontend
- Python FastAPI backend, including serving the static NextJS site at /
- Everything packaged into a Docker container
- Use "uv" as the package manager for python in the Docker container
- Use deepseek for the AI calls. An DEEPSEEK_API_KEY is in .env in the project root
- Use `deepseek-v4-pro` as the model
- Use SQLLite local database for the database, creating a new db if it doesn't exist
- Start and Stop server scripts for Mac, PC, Linux in scripts/

## Starting Point

A working MVP of the frontend has been built and is already in frontend. This is not yet designed for the Docker setup. It's a pure frontend-only demo.

## Color Scheme — "Harbor & Ember"

Low-saturation Pantone-inspired blue family paired with a muted brick-red accent. The blues stay calm and cool, while the red anchors emphasis without shouting.

- Deep Sea: `#1F3055` (Pantone 19-3919 TPX Insignia Blue) - main headings, primary text, deep surfaces
- Pacific Blue: `#487090` (Pantone 18-4032 TCX Riverside) - brand primary, CTAs, links, focus rings
- Aqua Mist: `#84A0B0` (Pantone 14-4214 TCX Stone Blue) - secondary highlight, badges, gradient mid-tone
- Coral Sunset: `#B5544A` (Pantone 18-1547 TCX Aurora Red) - red emphasis, warnings, attention dots
- Sand Dune: `#EDE0CC` (Pantone 13-1010 TCX Vanilla Cream) - warm neutral, soft surface tint, hover backgrounds
- Slate: `#888B8D` (Pantone 16-3915 TCX Alloy) - supporting text, labels, secondary content
- Foam: `#E2E8E5` (Pantone 12-4302 TCX Glacier Lake) - page background, palest cool surface

CSS variable names (in `frontend/src/app/globals.css`): `--deep-sea`, `--pacific-blue`, `--aqua-mist`, `--coral-sunset`, `--sand-dune`, `--slate`, `--foam`. The variable names are kept from the previous "Coastal Calm" palette so existing class names continue to work; only the colour values changed.

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.

## Working documentation

All documents for planning and executing this project will be in the docs/ directory.
Please review the docs/PLAN.md document before proceeding.