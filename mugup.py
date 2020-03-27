import argparse
import asyncio
import csv
from pathlib import Path
from slogan_images import validate_input, create_slogan_images
import render_mockups
import sys


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
    asyncio.run(
        render_mockups.main(
            infolder=Path("finished"),
            bucket="giftsondemand"
        )
    )
