# Companion language synchronization — 2026-11-01

Source implementation: companion 0.4.1, stable public identity unchanged. The
application still identifies as 1.3.0; this is unreleased development work.

## Behavior

- `ExtensionBridge.exchange` sends the live application language on every reply,
  including idle polls; the extension cannot set the application language through
  its message payload.
- The MV3 worker reads the language in its existing 1.5-second exchange. It stores
  semantic job states instead of bilingual display strings, then translates job
  and source descriptions for the active language. Old session state strings
  migrate when the worker restarts.
- The popup refreshes every two seconds and updates the document language,
  instructions, connection/empty messages, actions and source/protection labels.
  Focused/hovered buttons keep their node and candidate index during translation.
- Ten complete dictionaries ship locally: tr/en/de/es/fr/pt/ru/zh/ja/hi. Browser UI
  language is the first-connection fallback; the worker preserves the last app
  language in session storage after disconnect. Unsupported incoming language
  values cannot select arbitrary properties or trigger network requests.
- No new extension permissions, personal cookies, browser profile access, registry
  registration or translation service was added. Normal browser scheduling can
  delay timers; language changes should appear within a few seconds while the
  native connection/worker is active.

## Validation

- **36 Python tests passed**: extension bridge 16, companion setup 13, application
  language 7. Tests include live language changes without jobs, ignored extension
  language input, `/set-lang` propagation, actual native-host framing and fallback.
- **All 26 JavaScript UI suites passed.** New coverage verifies native reply
  changes, disconnect retention, popup sender isolation, all ten dictionary keys
  and placeholders, localized master/source labels and source URL privacy.
- Rendered popup acceptance passed all ten locales, initial French content,
  automatic live switch while a source button remains focused, the exact selected
  source index, translated disconnected content and logo loading. No script
  errors. Evidence: `build/extension-language-preview/result.json`, `popup-fr.png`
  and `popup-fr-disconnected.png`.
- A separate PyInstaller test package passed isolated startup and native-host
  checks. Changing the frozen application's language to French, Japanese and
  Turkish changed the real compiled native-host replies accordingly. Bundled
  companion 0.4.1 files match source and setup without consent remained blocked.
  Evidence: `build/language-sync-package-runtime/result.json`.

Test application: `build/language-sync-package/YoutubePro/YoutubePro.exe`;
keep its adjacent `_internal` directory. This is not a production installation.

The popup's browser fixture mocks runtime messages; the worker and real Python
native host are tested separately. This is not evidence for new website download
compatibility or a browser-store/production release.

## Adoption

Use the updated application, prepare its bundled companion in the setup wizard,
then reload the unpacked extension. Both halves must be updated: an older app
does not publish its live language, and an already loaded old extension cannot
acquire new translations without reloading its files.
