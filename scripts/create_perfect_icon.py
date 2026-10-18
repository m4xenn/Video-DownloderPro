from PIL import Image, ImageDraw

def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
    draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
    draw.pieslice([x0, y0, x0+radius*2, y0+radius*2], 180, 270, fill=fill)
    draw.pieslice([x1-radius*2, y0, x1, y0+radius*2], 270, 360, fill=fill)
    draw.pieslice([x0, y1-radius*2, x0+radius*2, y1], 90, 180, fill=fill)
    draw.pieslice([x1-radius*2, y1-radius*2, x1, y1], 0, 90, fill=fill)

ico_path = "icon.ico"
size = 256
# Make it 4x larger for anti-aliasing, then resize down
scale = 4
big_size = size * scale

img = Image.new("RGBA", (big_size, big_size), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

bg_color = (36, 40, 47, 255) # Matte dark grey
margin = 16 * scale
radius = 48 * scale
draw_rounded_rect(draw, [margin, margin, big_size-margin, big_size-margin], radius, bg_color)

# Draw white play triangle
triangle_color = (255, 255, 255, 255)
cx, cy = big_size // 2, big_size // 2
tw = 60 * scale
th = 70 * scale
p1 = (cx - tw//2 + 10*scale, cy - th//2)
p2 = (cx - tw//2 + 10*scale, cy + th//2)
p3 = (cx + tw//2 + 10*scale, cy)
draw.polygon([p1, p2, p3], fill=triangle_color)

# Resize down for anti-aliasing
img = img.resize((size, size), Image.Resampling.LANCZOS)
img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
print("Perfect transparent icon created!")
