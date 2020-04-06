import argparse
import csv
from math import ceil
import numpy as np
from pathlib import Path
from pdb import set_trace
from PIL import Image, ImageDraw, ImageFont
from progressbar import progressbar
from slogan_images import validate_input
import sys


def render_mugs(slogan_dicts):
    def draw_slogan(MAX_W, MAX_H):
        img = Image.new("RGBA", (MAX_W, MAX_H), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # font_map {corresponds to slogan.font, [path, size]}
        # Windows conversion problem in font paths but PIL
        # doesn't accept `Path` obj
        if sys.platform == "win32":
            font_map = {
                "abril": ["resources\\AbrilFatface-Regular.otf", 160],
                "amatic": ["resources\\AmaticSC-Regular.ttf", 580],
                "amatic-bold": ["resources\\Amatic-Bold.ttf", 580],
                "helvetica": ["resources\\Helvetica.otf", 160]
            }
        elif sys.platform == "darwin":
            font_map = {
                "abril": ["resources/AbrilFatface-Regular.otf", 160],
                "amatic": ["resources/AmaticSC-Regular.ttf", 387],
                "amatic-bold": ["resources/Amatic-Bold.ttf", 387],
                "helvetica": ["resources/Helvetica.otf", 640]
            }
        font = ImageFont.truetype(*font_map[slogan["font"]])

        slogan_lines = slogan["wrapped"]

        std_w, std_h = draw.textsize(slogan_lines[0], font=font)
        text_h = len(slogan_lines) * std_h
        starting_h = (MAX_H - text_h) / 2
        current_h = starting_h - 60

        for line in slogan["wrapped"]:
            w, h = draw.textsize(line, font=font)
            draw.text(((MAX_W - w) / 2, current_h), line, font=font, fill=(0, 0, 0))
            current_h += std_h

        return img

    def transform_slogan(original_img):
        def solve_quadratic_coeffs(point_1, point_2, point_3):
            points = points = np.array([point_1, point_2, point_3])
            x = points[:, 0]
            y = points[:, 1]
            z = np.polyfit(x, y, 2)
            return z

        def plot_deflected_point(x, a, b, height):
            return int(a * x ** 2 + b * x + height)

        def plot_alpha_point(x, d, e, f):
            return d * x ** 2 + e * x + f

        original_px = original_img.load()

        # The new image will be tallest on the bottom and in
        # the middle of the line.  So new height should be the
        # original height plus the new y value at the bottom of
        # the old image.
        original_w = original_img.size[0]
        original_h = original_img.size[1]

        # Quadratic for deflection found by fitting 3 points
        mid_x = original_w / 2
        deflection = 0.075
        mid_y = original_h * deflection

        # Deflection eqn coeffs
        a, b, c = solve_quadratic_coeffs(
            point_1=(0, 0),
            point_2=(mid_x, mid_y),
            point_3=(original_w, 0)
        )
        new_h = int(ceil(plot_deflected_point(mid_x, a, b, original_h)))
        new_img = Image.new("RGBA", (original_w, new_h), (255, 255, 255, 0))

        # Alpha (opacity) eqn found by fitting 3 points
        d, e, f = solve_quadratic_coeffs(
            point_1=(0, 0.6),
            point_2=(original_w / 4, 0.7),
            point_3=(mid_x, 0.8)
        )

        for x in range(original_w):  # cols
            for y in range(original_h):  # rows
                current_px = original_px[x, y]
                if current_px != (255, 255, 255, 0) and current_px != (0, 0, 0, 0):
                    if x < mid_x:
                        alpha_value = int(ceil(plot_alpha_point(x, d, e, f) * 255))
                    else:
                        reflected_x = 2 * mid_x - x
                        alpha_value = int(
                            ceil(plot_alpha_point(reflected_x, d, e, f) * 255)
                        )
                    new_px = (current_px[0], current_px[1], current_px[2], alpha_value)
                    new_px_y = plot_deflected_point(x, a, b, y)
                    try:
                        new_img.putpixel((x, new_px_y), new_px)
                    except Exception as e:
                        print(e)
                        set_trace()

        return new_img

    print("Create mug render images")
    slogans_with_path = []
    for slogan in progressbar(slogan_dicts):
        # STARTING_W, STARTING_H = 4900, 5100
        STARTING_W, STARTING_H = 1634, 1700
        slogan_img = draw_slogan(MAX_W=STARTING_W, MAX_H=STARTING_H)
        transformed_img = transform_slogan(slogan_img)

        # Calculate the resize by figuring out the final size.
        FINAL_W = 1372
        slogan_resize = FINAL_W / STARTING_W
        size = (
            int(ceil(STARTING_W * slogan_resize)),
            int(ceil(STARTING_H * slogan_resize))
        )
        transformed_img = transformed_img.resize(size, Image.ANTIALIAS)

        # paste onto left_mug_img
        left_mug_img = Image.open(Path("resources/mug_left_large.png"))
        left_mug_img.paste(transformed_img, (630, 180), transformed_img)

        # paste onto right_mug_img
        right_mug_img = Image.open(Path("resources/mug_right_large.png"))
        right_mug_img.paste(transformed_img, (-20, 180), transformed_img)

        # resize left_mug_image
        mug_resize = 0.5
        new_mug_w = int(ceil(left_mug_img.size[0] * mug_resize))
        new_mug_h = int(ceil(left_mug_img.size[1] * mug_resize))
        new_mug_size = (new_mug_w, new_mug_h)
        small_mug_img = left_mug_img.copy().resize((new_mug_size), Image.ANTIALIAS)

        # paste onto microwave_img
        microwave_img = Image.open(Path("resources/microwave.png"))
        microwave_img.paste(small_mug_img, (440, 45), small_mug_img)

        # paste onto size_example_img
        size_example_img = Image.open(Path("resources/size_example.png"))
        size_example_img.paste(small_mug_img, (440, 45), small_mug_img)

        # save
        render_path = Path(f"render/")
        Path(render_path).mkdir(parents=True, exist_ok=True)

        left_mug_path = Path(render_path / f"{slogan['name']}_left.png")
        left_mug_img.save(left_mug_path)
        slogan["left_mug_path"] = left_mug_path

        right_mug_path = Path(render_path / f"{slogan['name']}_right.png")
        right_mug_img.save(right_mug_path)
        slogan["right_mug_path"] = right_mug_path

        microwave_path = Path(render_path / f"{slogan['name']}_microwave.png")
        microwave_img.save(microwave_path)
        slogan["microwave_path"] = microwave_path

        size_example_path = Path(render_path / f"{slogan['name']}_size_example.png")
        size_example_img.save(size_example_path)
        slogan["size_example_path"] = size_example_path

        slogans_with_path.append(slogan)

    return slogans_with_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "-F",
        "--input_file",
        default="input.csv",
        help="Path to CSV with slogans and niches."
    )

    args = p.parse_args(sys.argv[1:])

    input_file = args.input_file
    with open(input_file, encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        slogan_dicts = [row for row in reader]

    Path("finished").mkdir(parents=True, exist_ok=True)
    valid_slogan_dicts = validate_input(slogan_dicts[:1])
    rendered_slogans = render_mugs(valid_slogan_dicts)
    set_trace()
