#!/usr/bin/env python3
"""
裂变海报生成器 — 陈星辰
依赖: pip3 install Pillow
用法: python3 poster_gen.py "苏婉清" "送人玫瑰，手有余香" template_rose output.png
"""
import sys
from PIL import Image, ImageDraw, ImageFont

def create_poster(name, quote, template, output):
    W, H = 1080, 1920
    
    # 渐变背景
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(233 + (248 - 233) * y / H)
        g = int(30 + (187 - 30) * y / H)
        b = int(99 + (208 - 99) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # 装饰圆
    draw.ellipse([W-200, -100, W+100, 200], fill=(255, 255, 255, 30))
    draw.ellipse([-100, H-300, 200, H], fill=(255, 255, 255, 20))
    
    # 玫瑰emoji (用文字替代)
    try:
        font_rose = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 120)
        draw.text((W//2-60, 200), "🌹", font=font_rose, fill=(0,0,0))
    except:
        draw.text((W//2-30, 250), "🌹", fill=(255,255,255))
    
    # 引号
    try:
        font_quote = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 80)
        font_text = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 52)
        font_name = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 36)
        font_brand = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 28)
    except:
        font_quote = font_text = font_name = font_brand = ImageFont.load_default()
    
    draw.text((120, 500), "“", font=font_quote, fill=(255, 255, 255, 200))
    
    # 金句 (自动换行)
    max_chars = 16
    lines = [quote[i:i+max_chars] for i in range(0, len(quote), max_chars)]
    y_start = 700
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_text)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x, y_start + i * 80), line, font=font_text, fill=(255, 255, 255))
    
    # 用户名
    name_text = f"—— {name}"
    bbox = draw.textbbox((0, 0), name_text, font=font_name)
    nw = bbox[2] - bbox[0]
    draw.text(((W - nw) // 2, y_start + len(lines) * 80 + 40), name_text, font=font_name, fill=(255, 215, 0))
    
    # 品牌
    brand = "予人玫瑰 · 让每个女性被看见"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) // 2, H - 200), brand, font=font_brand, fill=(255, 255, 255, 180))
    
    img.save(output)
    print(f"海报已生成: {output}")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "玫瑰女孩"
    quote = sys.argv[2] if len(sys.argv) > 2 else "送人玫瑰，手有余香"
    tpl = sys.argv[3] if len(sys.argv) > 3 else "template_rose"
    out = sys.argv[4] if len(sys.argv) > 4 else "poster.png"
    create_poster(name, quote, tpl, out)
