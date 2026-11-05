# Active recording edge verification

The user reported that the recording switched to real-time near 11% while still
appearing to contain earlier footage. The production 1.4.2 recording was inspected
read-only without stopping or modifying it.

## Evidence at the time of inspection

- Active progress: 3979.993111 recorded seconds, media pace 0.9682484484x,
  estimated remaining catch-up 2.584889 seconds. This is a momentary observation,
  not proof that every earlier transition was correct.
- Both selected HLS renditions exposed 720 five-second segments / 3600 seconds.
  Their latest program-time ends were approximately 4.0 and 4.8 seconds old.
- A frame extracted near the active MKV tail and a recent source frame showed
  the same broadcast scene and surrounding chat. A fresh independent YouTube
  extraction also returned a 3600-second window with a latest edge 5.1 seconds old.
- Stronger check: decode eight seconds of audio from the recent edge of a newly
  extracted source and cross-correlate against the active recording's last
  90 seconds at 8 kHz mono. Peak normalized correlation was **0.9919**. The sample
  ended **2.138 seconds before the extracted recording tail ended**. This is a
  match position, not a claim that total YouTube-to-recorder latency is 2.138 s.
- This confirms that current source audio had reached the end of the active file
  during the inspection. Hours of lag were not reproduced at that moment.
  The earlier hour naturally remains at the beginning of the same file.

The percentage represents recorded duration / the selected duration limit, not
the percentage of the broadcast archive. About 65 minutes in a ten-hour cap is
approximately 11%. The selected one-hour HLS window does not establish access to
all preceding hours of a broadcast.

Local numeric evidence is in `build/live-edge-investigation/audio-edge-match.json`
and `fresh-edge-result.json`. Read-only frame samples are in the same ignored
directory. Signed media URLs and raw source manifests were not written to these
reports. This check verifies the chosen source's current edge; no manual visual
comparison to the user's YouTube player was performed.

## Unpublished clarity changes

- Retain the initial offered history duration through the queue progress API.
- Display the initial offered history duration in the recording-state panel.
- Label the live percentage explicitly as **Recording limit** in all ten locales.
- Preserve the existing capture and phase calculation; no speed change or live
  recording restart was made. The public 1.4.2 release is unchanged.

Validation: live UI JavaScript checks and rendered UI assertions cover the history
duration and percentage label. Related queue/recovery/live suites run in an
isolated profile; local logs are under `build/live-edge-clarity-tests/` and
`build/live-edge-clarity-ui-final.log`.
