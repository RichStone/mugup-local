import argparse
import csv
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from progressbar import progressbar
from textwrap import wrap
import sys


def create_slogan_images(slogan_dicts):
    print("Create slogan images")
    slogans_with_path = []
    for slogan in progressbar(slogan_dicts):
        MAX_W, MAX_H = 1000, 915
        img = Image.new("RGB", (MAX_W, MAX_H), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # font_map {corresponds to slogan.font, [path, size]}
        # Windows conversion problem in font paths but PIL
        # doesn't accept `Path` obj
        if sys.platform == "win32":
            font_map = {
                "abril": ["resources\\AbrilFatface-Regular.otf", 155],
                "amatic": ["resources\\AmaticSC-Regular.ttf", 215],
                "amatic-bold": ["resources\\Amatic-Bold.ttf", 220],
                "helvetica": ["resources\\Helvetica.otf", 170]
            }
        elif sys.platform == "darwin":
            font_map = {
                "abril": ["resources/AbrilFatface-Regular.otf", 155],
                "amatic": ["resources/AmaticSC-Regular.ttf", 215],
                "amatic-bold": ["resources/Amatic-Bold.ttf", 220],
                "helvetica": ["resources/Helvetica.otf", 170]
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

        slogan_path = Path(f"finished/{slogan['name']}.png")
        img.save(slogan_path)
        slogan["slogan_path"] = slogan_path
        slogans_with_path.append(slogan)

    return slogans_with_path


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

    valid_slogan_dicts = validate_input(slogan_dicts)
    create_slogan_images(valid_slogan_dicts)
