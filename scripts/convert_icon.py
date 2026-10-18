from PIL import Image

# PNG dosyasının tam yolu
png_path = r"C:\Users\salih\.gemini\antigravity\brain\14870795-e9f9-4f80-952e-6e40e25bc8b3\app_icon_v3_1780542813060.png"
ico_path = "icon.ico"

# Resmi aç ve kaydet
img = Image.open(png_path)
img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
print("Icon başarıyla oluşturuldu!")
