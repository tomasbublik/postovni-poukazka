# Repository Guidelines

## Project Structure & Module Organization

This repository is a small, static browser tool for positioning print data on a Czech postal money order form.

- `postovni_poukazka_b.html` contains the full application: HTML, CSS, and JavaScript in one file.
- `poukazka-b.png` is the form background image loaded by the app.
- `docs/screenshot.png` is used by `README.md` to show the UI.
- `README.md` documents user-facing behavior and troubleshooting.

Keep new files minimal. Prefer extending the single HTML app unless a split into assets or modules clearly improves maintainability.

## Build, Test, and Development Commands

There is no package manager, build step, or dependency install.

- Open `postovni_poukazka_b.html` directly in a modern browser to run the app.
- Optional local server: `python3 -m http.server 8000`, then visit `http://localhost:8000/postovni_poukazka_b.html`.
- Check repository state with `git status --short` before committing.

## Coding Style & Naming Conventions

Use plain HTML, CSS, and browser JavaScript. Match the existing style:

- Two-space indentation.
- CSS class names use lowercase kebab-style names, for example `.sheet-wrap` and `.print-field`.
- JavaScript identifiers should be descriptive camelCase.
- Keep UI text in Czech to match the application and README.
- Avoid adding external dependencies unless the feature cannot be implemented reasonably with browser APIs.

## Testing Guidelines

No automated tests are currently configured. Validate changes manually in a browser:

- Confirm the app loads with `poukazka-b.png`.
- Check form input editing, positioning by click, JSON export/import, debug display, and print preview.
- For print-related changes, test 100% scale with browser print preview and avoid layout shifts.

If automated tests are added later, document the command in this file and keep tests focused on positioning/state logic.

## Commit & Pull Request Guidelines

Git history uses short, direct commit messages such as `Added screenshot` and `Finished`. Prefer concise imperative or past-tense summaries, for example `Update print positioning controls`.

Pull requests should include:

- A short description of the user-visible change.
- Manual validation steps and tested browser(s).
- Screenshots when the UI or printed layout changes.
- Notes about any changed defaults, local storage keys, or expected print settings.

## Agent-Specific Instructions

Do not remove or replace `poukazka-b.png` unless explicitly asked. Preserve the static, offline-friendly nature of the tool and avoid broad refactors unrelated to the requested change.
