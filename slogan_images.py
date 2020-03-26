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
    valid_slogans = []
    for slogan in slogan_dicts:
        error_obj = {
            "row": int,
            "error_count": int,
            "error": ["error 1", "error n"]
        }

        error_obj["row"] = slogan_dicts.index(slogan) + 2
        error_obj["error"] = []

        # Check font
        font_map = {
            "abril": {"max_chars": 12, "max_lines": 4},
            "amatic": {"max_chars": 14, "max_lines": 4},
            "amatic-bold": {"max_chars": 14, "max_lines": 5},
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
    set_trace()
    create_slogan_images(valid_slogan_dicts)
