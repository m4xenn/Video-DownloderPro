import re

file_path = r"C:\Users\salih\Desktop\HTML\YoutubePro\templates\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add CDN
cdn_link = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/lipis/flag-icons@7.0.0/css/flag-icons.min.css"/>\n    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
content = content.replace('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">', cdn_link)

# Replace trigger innerText to innerHTML
content = content.replace("document.getElementById('currentLangFlag').innerText = t.flag;", "document.getElementById('currentLangFlag').innerHTML = t.flag;")

# Replace emojis in translations dictionary
emoji_map = {
    '🇹🇷': '<span class="fi fi-tr"></span>',
    '🇬🇧': '<span class="fi fi-gb"></span>',
    '🇪🇸': '<span class="fi fi-es"></span>',
    '🇫🇷': '<span class="fi fi-fr"></span>',
    '🇩🇪': '<span class="fi fi-de"></span>',
    '🇷🇺': '<span class="fi fi-ru"></span>',
    '🇵🇹': '<span class="fi fi-pt"></span>',
    '🇨🇳': '<span class="fi fi-cn"></span>',
    '🇯🇵': '<span class="fi fi-jp"></span>',
    '🇮🇳': '<span class="fi fi-in"></span>'
}

for emoji, html in emoji_map.items():
    content = content.replace(f'flag: "{emoji}"', f"flag: '{html}'")
    content = content.replace(f'>{emoji} ', f'>{html} ')
    content = content.replace(f'>{emoji}<', f'>{html}<')

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated index.html with flag icons!")
