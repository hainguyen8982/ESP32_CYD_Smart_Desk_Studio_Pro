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
    img.save(os.path.join(assets_dir, "vol_up.png"))
    
    print("PNG Media Icons generated successfully in assets/!")

if __name__ == "__main__":
    create_icons()
