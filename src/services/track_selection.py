"""Source-declared track languages and strict, injection-safe selections."""
import re

LANGUAGE = re.compile(r'[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*\Z')


def valid_language(value):
    return isinstance(value, str) and len(value) <= 35 and bool(LANGUAGE.fullmatch(value))


def track_choices(info):
    audio = {f.get('language') for f in info.get('formats', [])
             if f.get('acodec') not in (None, 'none') and not f.get('has_drm')
             and valid_language(f.get('language'))}
    subtitles = {lang for lang, tracks in (info.get('subtitles') or {}).items()
                 if tracks and valid_language(lang)}
    return {'audio_languages': sorted(audio), 'subtitle_languages': sorted(subtitles)}


def normalize_tracks(options):
    audio, subtitle = options.get('audio_language', 'auto'), options.get('subtitle_language', 'all')
    if (audio != 'auto' and not valid_language(audio)) or (subtitle != 'all' and not valid_language(subtitle)):
        raise ValueError('Invalid track language.')
    if options.get('format') == 'audio' or not options.get('embed_subs'):
        subtitle = 'all'
    return {'audio_language': audio, 'subtitle_language': subtitle}


def apply_tracks(ydl_options, options):
    tracks = normalize_tracks(options)
    if tracks['audio_language'] != 'auto':
        # Every audio-bearing fallback must honour the choice. Never silently switch language.
        ydl_options['format'] = re.sub(r'\b(bestaudio|best)(?=\[|\+|/|\s|$)',
            lambda match: match[0] + '[language=' + tracks['audio_language'] + ']', ydl_options['format'])
    ydl_options['subtitleslangs'] = [tracks['subtitle_language']]


def validate_subtitle_choice(info, options):
    """Recheck after resolving a fresh URL, before downloading media bytes."""
    language = normalize_tracks(options)['subtitle_language']
    if language != 'all' and not (info.get('subtitles') or {}).get(language):
        raise ValueError('Selected subtitle language is no longer available. Refresh the video / Seçilen altyazı artık sunulmuyor. Videoyu yeniden inceleyin.')
