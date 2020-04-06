import argparse
import boto3
import csv
from datetime import date
from math import ceil
import numpy as np
from pathlib import Path
from pdb import set_trace
from PIL import Image, ImageDraw, ImageFont
from progressbar import progressbar
from shutil import rmtree
import sys
from textwrap import wrap


def validate_input(slogan_dicts):
    def clean_whitespace(string):
        string_split = string.split()
        return " ".join(string_split)
    today = date.today().strftime("%Y%m%d")
    errors = []
    valid_slogans = []
    print("Validate slogans")
    for slogan in progressbar(slogan_dicts):
        slogan["slogan"] = clean_whitespace(slogan["slogan"])
        slogan["niche"] = clean_whitespace(slogan["niche"]).replace(" ", "-").lower()
        slogan["row"] = slogan_dicts.index(slogan) + 2
        slogan["name"] = f"{slogan['niche']}_{slogan_dicts.index(slogan)}_{today}"
        error_obj = {
            "row": int,
            "error_count": int,
            "error": ["error 1", "error n"]
        }

        error_obj["row"] = slogan["row"]
        error_obj["error"] = []

        # Check font
        font_map = {
            "abril": {"max_chars": 12, "max_lines": 5},
            "amatic": {"max_chars": 14, "max_lines": 4},
            "amatic-bold": {"max_chars": 14, "max_lines": 4},
            "helvetica": {"max_chars": 12, "max_lines": 5}
        }
        try:
            if not slogan["font"]:
                slogan["font"] = "abril"
            limits_dict = font_map[slogan["font"]]
            slogan["max_chars"] = limits_dict["max_chars"]
            slogan["max_lines"] = limits_dict["max_lines"]
        except KeyError:
            error_obj["error"].append("Font not found. Options are abril, amatic, amatic-bold, helvetica.  Check for spaces")  # noqa: E501
            slogan["max_chars"] = 14
            slogan["max_lines"] = 4
            try:
                error_obj["error_count"] += 1
            except TypeError:
                error_obj["error_count"] = 1

        # Check word length < max_chars
        individual_words = slogan["slogan"].split()
        words_exceeding_char_limit = 0
        for word in individual_words:
            word_len = len(word)
            if word_len > slogan["max_chars"]:
                words_exceeding_char_limit += 1
        if words_exceeding_char_limit > 0:
            error_obj["error"].append(f"{words_exceeding_char_limit} word(s) exceed(s) character limit.  Must be less than chars {slogan['max_chars']} for this font")  # noqa:E501
            try:
                error_obj["error_count"] += 1
            except TypeError:
                error_obj["error_count"] = 1

        # Check num of lines when wrapped
        slogan["wrapped"] = wrap(slogan["slogan"], width=slogan["max_chars"])
        num_of_lines = len(slogan["wrapped"])
        if num_of_lines > slogan["max_lines"]:
            error_obj["error"].append(f"Too many lines.  Make the slogan shorter")  # noqa:E501
            try:
                error_obj["error_count"] += 1
            except TypeError:
                error_obj["error_count"] = 1

        # Append to `errors` list if any present
        errors_present = type(error_obj["error_count"]) is int
        if errors_present:
            # convert errors to one string
            error_str = ""
            for idx, error in enumerate(error_obj["error"]):
                idx += 1
                new_str = f"#{idx} - {error} "
                error_str += new_str
            error_obj["error"] = error_str
            errors.append(error_obj)
        else:
            valid_slogans.append(slogan)

    # output csv with errors lists
    if len(errors) > 0:
        keys = errors[0].keys()
        with open("slogan_errors.csv", "w") as error_output:
            dict_writer = csv.DictWriter(error_output, keys)
            dict_writer.writeheader()
            dict_writer.writerows(errors)

    return valid_slogans


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

        # paste onto microwave_mug_img
        microwave_mug_img = Image.open(Path("resources/microwave_mug.png"))
        microwave_mug_img.paste(small_mug_img, (440, 45), small_mug_img)

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

        microwave_mug_path = Path(render_path / f"{slogan['name']}_microwave_mug.png")
        microwave_mug_img.save(microwave_mug_path)
        slogan["microwave_mug_path"] = microwave_mug_path

        size_example_path = Path(render_path / f"{slogan['name']}_size_example.png")
        size_example_img.save(size_example_path)
        slogan["size_example_path"] = size_example_path

        slogans_with_path.append(slogan)

    return slogans_with_path


def upload_mugs_to_s3(slogan_dicts):
    print("Upload mug renders to S3")
    AWS_ACCESS_KEY_ID = "AKIAINCEUCJHE3FHXWBQ"
    AWS_SECRET_ACCESS_KEY = "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"
    bucket = "giftsondemand"
    today_str = str(date.today())

    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    slogans_with_mug_urls = []
    for slogan in progressbar(slogan_dicts):
        try:
            images_to_upload_paths = {
                "left_mug": slogan["left_mug_path"],
                "right_mug": slogan["right_mug_path"],
                "microwave_mug": slogan["microwave_mug_path"],
                "size_example": slogan["size_example_path"]
            }
            for key, local_img_path in images_to_upload_paths.items():
                s3_img_path = f"{today_str}/{local_img_path.name}"
                with open(local_img_path, "rb") as f:
                    s3.put_object(
                        Bucket=bucket,
                        Key=s3_img_path,
                        Body=f,
                        ContentType="image/png",
                        ACL="public-read"
                    )
                # Example finished AWS S3 URL
                # https://giftsondemand.s3.amazonaws.com/2020-01-07/10_r.png
                aws_url = f"https://{bucket}.s3.amazonaws.com/{s3_img_path}"
                slogan[f"{key}_url"] = aws_url
            slogans_with_mug_urls.append(slogan)
            set_trace()
        except Exception as e:
            print(e)
            set_trace()

    rmtree(Path(f"render/"))

    return slogans_with_mug_urls


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
    valid_slogan_dicts = validate_input(slogan_dicts)
    rendered_slogans = render_mugs(valid_slogan_dicts)
    uploaded_mugs = upload_mugs_to_s3(rendered_slogans)
    set_trace()
