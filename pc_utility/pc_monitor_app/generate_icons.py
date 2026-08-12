import os
from PIL import Image, ImageDraw

def create_icons():
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    # 1. PREV ICON (#818CF8)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (129, 140, 248, 255)
    draw.rounded_rectangle([10, 16, 17, 48], radius=2, fill=color)
    draw.polygon([(36, 16), (19, 32), (36, 48)], fill=color)
    draw.polygon([(55, 16), (38, 32), (55, 48)], fill=color)
    img.save(os.path.join(assets_dir, "prev.png"))

    # 2. PLAY_PAUSE ICON (#39FF14)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (57, 255, 20, 255)
    draw.polygon([(10, 16), (28, 32), (10, 48)], fill=color)
    draw.rounded_rectangle([36, 16, 44, 48], radius=2, fill=color)
    draw.rounded_rectangle([49, 16, 57, 48], radius=2, fill=color)
    img.save(os.path.join(assets_dir, "play_pause.png"))

    # 3. NEXT ICON (#818CF8)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (129, 140, 248, 255)
    draw.polygon([(9, 16), (26, 32), (9, 48)], fill=color)
    draw.polygon([(28, 16), (45, 32), (28, 48)], fill=color)
    draw.rounded_rectangle([47, 16, 54, 48], radius=2, fill=color)
    img.save(os.path.join(assets_dir, "next.png"))

    # 4. VOL_DOWN ICON (#FBBF24)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (251, 191, 36, 255)
    draw.rounded_rectangle([8, 24, 18, 40], radius=2, fill=color)
    draw.polygon([(18, 24), (32, 14), (32, 50), (18, 40)], fill=color)
    draw.rounded_rectangle([40, 29, 56, 35], radius=2, fill=color)
    img.save(os.path.join(assets_dir, "vol_down.png"))

    # 5. MUTE ICON (#F85149)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (248, 81, 73, 255)
    draw.rounded_rectangle([8, 24, 18, 40], radius=2, fill=color)
    draw.polygon([(18, 24), (32, 14), (32, 50), (18, 40)], fill=color)
    draw.line([(40, 22), (56, 42)], fill=color, width=5)
    draw.line([(40, 42), (56, 22)], fill=color, width=5)
    img.save(os.path.join(assets_dir, "mute.png"))

    # 6. VOL_UP ICON (#FBBF24)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (251, 191, 36, 255)
    draw.rounded_rectangle([8, 24, 18, 40], radius=2, fill=color)
    draw.polygon([(18, 24), (32, 14), (32, 50), (18, 40)], fill=color)
    draw.rounded_rectangle([40, 29, 56, 35], radius=2, fill=color)
    draw.rounded_rectangle([45, 24, 51, 40], radius=2, fill=color)
    # 7. PORT ICON (#38BDF8) - USB Plug / Serial Cable
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (56, 189, 248, 255)
    draw.rounded_rectangle([18, 10, 46, 28], radius=3, fill=color)
    draw.rectangle([24, 16, 28, 22], fill=(15, 23, 42, 255))
    draw.rectangle([36, 16, 40, 22], fill=(15, 23, 42, 255))
    draw.rounded_rectangle([14, 28, 50, 46], radius=4, fill=color)
    draw.rounded_rectangle([28, 46, 36, 58], radius=2, fill=color)
    img.save(os.path.join(assets_dir, "port.png"))

    # 8. REFRESH ICON (#34D399) - Reload Circular Arrow
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (52, 211, 153, 255)
    draw.arc([10, 10, 54, 54], start=30, end=300, fill=color, width=7)
    draw.polygon([(46, 8), (58, 22), (38, 24)], fill=color)
    img.save(os.path.join(assets_dir, "refresh.png"))

    # 9. TAB LIVE CONTROL CENTER ICON (#38BDF8) - Desktop Screen + Control Sliders
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (56, 189, 248, 255)
    draw.rounded_rectangle([8, 10, 56, 42], radius=4, fill=color)
    draw.rectangle([14, 16, 50, 36], fill=(15, 23, 42, 255))
    draw.rectangle([28, 42, 36, 50], fill=color)
    draw.rounded_rectangle([20, 50, 44, 54], radius=2, fill=color)
    draw.polygon([(26, 20), (40, 26), (26, 32)], fill=color)
    img.save(os.path.join(assets_dir, "tab_live.png"))

    # 10. TAB SKIN DESIGNER STUDIO ICON (#F472B6) - Paint Palette / Brush
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (244, 114, 182, 255)
    draw.ellipse([8, 10, 56, 54], fill=color)
    draw.ellipse([14, 16, 50, 48], fill=(15, 23, 42, 255))
    draw.ellipse([20, 22, 28, 30], fill=(56, 189, 248, 255))
    draw.ellipse([34, 18, 42, 26], fill=(57, 255, 20, 255))
    draw.ellipse([42, 32, 50, 40], fill=(251, 191, 36, 255))
    draw.ellipse([18, 36, 26, 44], fill=color)
    img.save(os.path.join(assets_dir, "tab_designer.png"))

    # 11. TAB SYSTEM SETTINGS ICON (#FBBF24) - Gear Cogwheel
    import math
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (251, 191, 36, 255)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = 32 + int(22 * math.cos(rad))
        y1 = 32 + int(22 * math.sin(rad))
        draw.ellipse([x1-5, y1-5, x1+5, y1+5], fill=color)
    draw.ellipse([14, 14, 50, 50], fill=color)
    draw.ellipse([24, 24, 40, 40], fill=(15, 23, 42, 255))
    img.save(os.path.join(assets_dir, "tab_settings.png"))
    
    print("PNG Media, Port & Tab Icons generated successfully in assets/!")

if __name__ == "__main__":
    create_icons()
