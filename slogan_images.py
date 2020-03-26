import argparse
import csv
from datetime import date
from pathlib import Path
from pdb import set_trace
from PIL import Image, ImageDraw, ImageFont
from textwrap import wrap
import sys


class Slogan():
    def __init__(self, *, name, slogan, niche, font):
        self.name = name
        self.valid_slogan = None
        self.slogan = slogan
        self.wrapped = wrap(slogan, width=14)
        self.niche = niche
        self.font = font.lower()

    def __repr__(self):
        return self.name


def create_slogan_images(slogan_dicts):
    def standardize_whitespace(string):
        string_split = string.split()
        return " ".join(string_split)

    def create_slogan_objects(slogan_list):
        today = date.today().strftime("%Y%m%d")
        slogan_objs = []
        for slogan in slogan_list:
            niche = standardize_whitespace(slogan["niche"])
            niche = niche.replace(" ", "-").lower()
            name = f"{slogan_list.index(slogan)}_{today}_{niche}"
            slogan_objs.append(
                Slogan(
                    name=name,
                    slogan=slogan["slogan"],
                    niche=slogan["niche"],
                    font=slogan["font"]
                )
            )
        return slogan_objs

    def create_slogan_drawings(slogan_objs):
        for slogan in slogan_objs:
            MAX_W, MAX_H = 1000, 915
            img = Image.new("RGB", (MAX_W, MAX_H), (255, 255, 255))
            draw = ImageDraw.Draw(img)

            # font_map {corresponds to slogan.font, [path, size]}
            # Windows conversion problem in font paths but PIL
            # doesn't accept `Path` obj
            font_map = {
                "abril": ["fonts/AbrilFatface-Regular.otf", 108],
                "amatic": ["fonts/AmaticSC-Regular.ttf", 220],
                "amatic-bold": ["fonts/Amatic-Bold.ttf", 220],
                "helvetica": ["fonts/Helvetica.otf", 110]
            }
            font = ImageFont.truetype(*font_map[slogan.font])

            current_h, pad = 0, 0
            for line in slogan.wrapped:
                w, h = draw.textsize(line, font=font)
                draw.text(((MAX_W - w) / 2, current_h), line, font=font, fill=(0, 0, 0))
                current_h += h + pad

            out_file = Path(f"finished/{slogan.name}.png")
            img.save(out_file)

    slogan_objs = create_slogan_objects(slogan_dicts)
    create_slogan_drawings(slogan_objs)


def validate_input(slogan_dicts):
    errors = []

    for slogan in slogan_dicts:
        error_obj = {
            "row": int,
            "error_count": int,
            "error": ["error 1", "error n"]
        }

        error_obj["row"] = slogan_dicts.index(slogan)
        error_obj["error"] = []

        # Check font
        font_map = {
            "abril": {"max_chars": 12, "max_lines": 4},
            "amatic": {"max_chars": 14, "max_lines": 4},
            "amatic-bold": {"max_chars": 14, "max_lines": 4},
            "helvetica": {"max_chars": 12, "max_lines": 4}
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

        # Append to `errors` list if any present
        errors_present = type(error_obj["error_count"]) is int
        if errors_present:
            errors.append(error_obj)
    set_trace()
    # output csv with errors lists


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

    validated_slogan_dicts = validate_input(slogan_dicts)
    create_slogan_images(validated_slogan_dicts)
