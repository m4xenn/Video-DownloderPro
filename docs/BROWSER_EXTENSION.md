# Browser companion — guided setup (0.4.1, bundled with 1.4.0)

New packaged builds include the extension, its icons and the native bridge. No Python, PowerShell command, extension ID copying or separate helper download is required for end users. Upgrade the application to 1.4.0 to get the wizard; installed v1.3.0 does not gain it automatically.

## End-user flow

1. Open **Settings → Browser companion** (also linked from the welcome tour and User guide).
2. Choose installed Chrome, Edge or Brave, explicitly allow the local connection, then choose **Prepare setup**.
3. Choose **Open extensions page**. In the browser, enable Developer mode and choose **Load unpacked**.
4. Choose **Copy folder path** in the app. In the browser's folder picker, press Ctrl+L, paste, press Enter, then Select Folder. **Show folder** is also available.
5. Open the companion icon and return to **Check connection**. The app reports connected only after the correct extension identity and current version send a heartbeat.
6. Paste a video page into the application. If playback is needed, choose **Open video in browser** in the app to focus the pending app-owned tab. Play the video there; a verified source returns automatically. Choose **All qualities** in the companion only when multiple sources are ambiguous; quality selection and download stay in the app.

The browser still requires the user to load/approve the extension. This unpacked preview is not installed silently and is not a store-published extension. A store listing can simplify the browser step later, but store publishing is separate work.

## User consent, identity and scope

Preparing setup copies bundled files into the current user's LocalAppData and registers this companion's native host in HKCU. Only the public-key-derived extension ID is added to allowed origins; previously approved IDs are preserved. Brave uses the Chrome-compatible host key in tested Windows builds. Registry writes are never performed on startup, status checks, or without the setup checkbox. Chrome and Brave share their native registration key; removing that key disconnects both.

The fixed public manifest key keeps extension identity stable across installation folders and machines. It is public identity material, not a signing private key. Existing 0.1.x unpacked previews used a path-derived ID: load the new prepared folder and remove the old preview once the new connection is verified. Do not regenerate the public key between builds.

Permissions are native messaging, web requests, alarms, session storage and HTTP/HTTPS site access. Code tracks only tabs opened for app jobs. Sources/labels remain in memory or browser session storage, not permanent browsing logs. No profile copying, cookie or Authorization capture, CAPTCHA solving, DRM bypass, Shields changes or browser security changes are performed. Cookie-bound sources may still fail.

## Assets and build

The extension uses the app's lime download-arrow logo in 16/32/48/128px PNG icons and its popup header. The setup guide and help captures support all ten app languages.

`scripts/build_release.py` builds the standalone console native host before `YoutubePro.spec`. The spec includes `browser-extension/` and `dist/BrowserBridge/VDPBrowserBridge.exe` inside application resources, so Inno's existing recursive app copy includes both. There is no silent browser registration in the installer; the desktop wizard performs it after consent as the current user.

For development only, build the native host with:
`python -m PyInstaller --onefile --console --name VDPBrowserBridge --distpath dist/BrowserBridge --workpath build/browser-host --specpath build/browser-host scripts/extension_native_host.py`

Then run the source app or build `YoutubePro.spec`. The manual registration script remains a developer fallback and accepts `-Browser Brave`, `Chrome`, `Edge` or `All`. Never silently register a new extension identity on an existing user's computer.

## Validation and limits

- 361 isolated Python tests passed, including consent/no-write cases, invalid browser/action rejection, preserved origins, stable identity, Unicode profile paths and API origin protection.
- All JavaScript UI suites passed, including source-label classification and source-selection identity.
- The guided UI passed consent, preparation, browser action, folder display, all ten language changes and live connection status in an isolated fixture. OS registration was mocked there.
- Ten real UI captures with example data were generated for the welcome tour/User guide.
- An isolated installed Brave test passed automatic blob/HLS handoff via the real extension, compiled native host and GenericResolver, including current-version heartbeat status. It used a separate test host name/key and preserved personal registration/profile.
- A frozen app smoke test verified bundled extension/icons/help/native executable, rejected setup without consent without writing local setup files, and exchanged real native stdio frames with the frozen bridge. It wrote no native-host registration keys.
- Earlier Aile Planı testing passed user-assisted discovery, metadata and a 16 KiB HTTP 206 sample. The new wizard does not imply a fresh full-film or installer-upgrade acceptance test.

Native messaging references: [Chrome](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging), [Edge](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/developer-guide/native-messaging).

## 0.3.0 compatibility milestone

HLS observations can now be selected automatically when explicit master references prove that every same-frame candidate belongs to one acyclic presentation. Independent/ad roots still require user selection. Subtitle playlists are labelled separately. Known DRM and unsupported encryption manifests are disabled in source selection; standard AES-128/identity is not mislabeled DRM. The content script observes encrypted events from document start instead of treating an attached MediaKeys object alone as proof of encryption.

The corresponding application source adds bounded typed HLS parsing, split-rendition combination, subtitle preservation and embedded output stream validation. This is still unreleased source work; the earlier frozen 0.2.0 setup smoke test is not a fresh frozen 0.3.0 download acceptance. See [compatibility priorities](COMPATIBILITY_ROADMAP.md) and [test report](testing/HLS_DRM_COMPATIBILITY_2026-10-30.md).

## 0.4.0 download follow-up

Repeated inspections of the same page share one pending job rather than opening duplicate tabs. Focusing a tab requires an explicit app action and targets only its pending owned job. Playing live videos can be observed; DASH requests and explicit preview markers are handed to the application. Preview detection does not grant full-source access. See [download improvements acceptance](testing/DOWNLOAD_IMPROVEMENTS_2026-10-30.md).

## 0.4.1 application language synchronization

Every native bridge reply includes the application's current supported language,
even with no pending video jobs. The worker uses the existing 1.5-second polling
exchange and the popup refreshes every two seconds while open. Timer scheduling
is subject to the browser's worker lifecycle; these are not hard timing promises.

All ten application languages cover popup instructions, disconnected/empty
states, job progress, source/quality/audio/subtitle labels and protection notices.
Before the first app connection, the browser UI language is used (English for
unsupported languages). The worker retains the last matched app language in
session storage across disconnection/restarts within the browser session. Language
changes update focused/hovered source labels in place without changing the source
index or detaching the control during interaction.

This requires both the updated application and extension. Close the older app,
open application version 1.4.0 or newer, use the companion wizard to prepare the updated files
with the usual consent, then reload the existing unpacked extension on the
browser's extensions page. The stable extension identity/key and permissions are
unchanged; no new native-host program or permission is required for this protocol
addition. Browser-store publication and installed production upgrades remain
separate steps.
