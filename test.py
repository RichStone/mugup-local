from PIL import Image, ImageDraw, ImageFont
import textwrap

slogan_list = ["12345678901234 1234567",
               "Here's slogan 1.  There are no line breaks built in.",
               "Second slogan, I choose you!  Piikkaaa!"]
para = textwrap.wrap(slogan_list[0], width=14)

MAX_W, MAX_H = 1000, 915
img = Image.new("RGB", (MAX_W, MAX_H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("fonts/Helvetica.otf", 130)

current_h, pad = 0, 0
for line in para:
    w, h = draw.textsize(line, font=font)
    draw.text(((MAX_W - w) / 2, current_h), line, font=font)
    current_h += h + pad

img.save("test.png")
