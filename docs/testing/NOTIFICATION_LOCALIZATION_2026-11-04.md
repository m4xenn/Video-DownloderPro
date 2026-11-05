# Warning language and completion notification preferences

Implemented in the unpublished 1.4.3 source. Public 1.4.2 is unchanged.

- Shared message catalog covers ten UI languages, with stable response keys and parameter substitution. API warning text follows the active UI language; a response received after a language change renders from its key using the current language.
- Queue errors, source stages, component update notices, diagnostic actions and browser interaction messages use the shared catalog. Existing recovery/native lifecycle/companion catalogs remain in use. Technical diagnostic report contents retain their technical language.
- Settings offers completion notifications **always**, **background only**, or **never**. Default is always, preserving prior behavior. The policy is applied immediately before starting a Windows notification thread; background mode checks foreground/root-owner process identity.
- The completion message resolves the latest selected language when the queue completes. Preferences survive settings edits and restarts.

Validation:

- Full isolated Python regression: **524 tests, zero failures/errors** (`build/notification-regression/result.json`). Two additional foreground-owner/latest-language tests were added after discovery; all seven focused preference tests pass.
- All **27 JavaScript test files** pass.
- Rendered UI: all ten notification labels/options and queue error languages, save/reload preservation and keyed response translation pass without page errors (`build/notification-ui/result.json`). French settings screenshot inspected.
- Actual frozen Windows EXE: isolated launch, French API warning, invalid preference rejection, saved background preference, restart preservation and eight matching asset files pass (`build/notification-native/result.json`). No personal profile changes or real notifications were needed.

Current preview: `build/localized-notifications-package/YoutubePro/YoutubePro.exe` (keep its `_internal` directory alongside it).
Executable SHA-256: `2ebe0e42e33eecc41c4d3044396df0d9662df4cd30202c8f2cc5c6a1b4b52f5f`.

The older installer under `releases/v1.4.3` does **not** contain these changes or the subsequent startup polish. It must be rebuilt and validated before publication. No release was published during this task.
