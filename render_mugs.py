import argparse
import boto3
import csv
from datetime import date, datetime
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

    print("Clean out blank lines")
    slogan_dicts_no_blank_lines = []
    for slogan in progressbar(slogan_dicts):
        if slogan["slogan"] != "":
            slogan_dicts_no_blank_lines.append(slogan)

    today = date.today().strftime("%Y%m%d")
    errors = []
    valid_slogans = []
    print("Validate slogans")
    for slogan in progressbar(slogan_dicts_no_blank_lines):
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


def render_mugs(valid_slogan_dicts):
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
    for slogan in progressbar(valid_slogan_dicts):
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


def upload_mugs_to_s3(rendered_slogan_dicts):
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
    for slogan in progressbar(rendered_slogan_dicts):
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
        except Exception as e:
            print(e)
            set_trace()

    rmtree(Path(f"render/"))

    return slogans_with_mug_urls


def create_amazon_upload_file(uploaded_mugs_dicts):
    print("Format dict for csv printing")
    formatted_dicts = []
    today_str = date.today().strftime("%Y%m%d")

    for i, slogan_dict in progressbar(enumerate(uploaded_mugs_dicts)):
        formatted_dict = {}
        formatted_dict["feed_product_type"] = "kitchen"
        formatted_dict["item_sku"] = f"{today_str}-{i}"
        formatted_dict["brand_name"] = "Gifts On Demand"
        formatted_dict["item_name"] = slogan_dict["item_name"]
        formatted_dict["external_product_id"] = ""
        formatted_dict["external_product_id_type"] = "UPC"
        formatted_dict["item_type"] = "novelty-coffee-mugs"
        formatted_dict["standard_price"] = 19.95
        formatted_dict["quantity"] = 99
        formatted_dict["main-image-url"] = slogan_dict["left_mug_url"]
        formatted_dict["other-image-url1"] = slogan_dict["right_mug_url"]
        formatted_dict["other-image-url2"] = slogan_dict["microwave_mug_url"]
        formatted_dict["other-image-url3"] = slogan_dict["size_example_url"]
        formatted_dict["other-image-url4"] = ""
        formatted_dict["other-image-url5"] = ""
        formatted_dict["other-image-url6"] = ""
        formatted_dict["other-image-url7"] = ""
        formatted_dict["other-image-url8"] = ""
        formatted_dict["swatch-image-url"] = ""
        formatted_dict["parent_child"] = ""
        formatted_dict["parent_sku"] = ""
        formatted_dict["relationship_type"] = ""
        formatted_dict["variation_theme"] = ""
        formatted_dict["update_delete"] = ""
        formatted_dict["product_description"] = ""
        formatted_dict["manufacturer"] = ""
        formatted_dict["part_number"] = ""
        formatted_dict["model"] = ""
        formatted_dict["closure_type"] = ""
        formatted_dict["bullet_point1"] = "High quality mug makes the perfect gift for everyone."  # noqa:E501
        formatted_dict["bullet_point2"] = "Printed on only the highest quality mugs. The print will never fade no matter how many times it is washed."  # noqa:E501
        formatted_dict["bullet_point3"] = "Packaged, and shipped from the USA."
        formatted_dict["bullet_point4"] = "Dishwasher and Microwave safe."
        formatted_dict["bullet_point5"] = "Shipped in a custom made styrofoam package to ensure it arrives perfect. GUARANTEED."  # noqa:E501
        formatted_dict["target_audience_base"] = ""
        formatted_dict["catalog_number"] = ""
        formatted_dict["specific_uses_keywords1"] = ""
        formatted_dict["specific_uses_keywords2"] = ""
        formatted_dict["specific_uses_keywords3"] = ""
        formatted_dict["specific_uses_keywords4"] = ""
        formatted_dict["specific_uses_keywords5"] = ""
        formatted_dict["target_audience_keywords1"] = ""
        formatted_dict["target_audience_keywords2"] = ""
        formatted_dict["target_audience_keywords3"] = ""
        formatted_dict["thesaurus_attribute_keywords1"] = ""
        formatted_dict["thesaurus_attribute_keywords2"] = ""
        formatted_dict["thesaurus_attribute_keywords3"] = ""
        formatted_dict["thesaurus_attribute_keywords4"] = ""
        formatted_dict["thesaurus_subject_keywords1"] = ""
        formatted_dict["thesaurus_subject_keywords2"] = ""
        formatted_dict["thesaurus_subject_keywords3"] = ""
        formatted_dict["generic_keywords"] = slogan_dict["keywords"]
        formatted_dict["platinum_keywords1"] = ""
        formatted_dict["platinum_keywords2"] = ""
        formatted_dict["platinum_keywords3"] = ""
        formatted_dict["platinum_keywords4"] = ""
        formatted_dict["platinum_keywords5"] = ""
        formatted_dict["country_as_labeled"] = ""
        formatted_dict["fur_description"] = ""
        formatted_dict["occasion"] = ""
        formatted_dict["number_of_pieces"] = ""
        formatted_dict["scent_name"] = ""
        formatted_dict["included_components"] = ""
        formatted_dict["color_name"] = "white"
        formatted_dict["color_map"] = ""
        formatted_dict["size_name"] = ""
        formatted_dict["material_type"] = ""
        formatted_dict["style_name"] = ""
        formatted_dict["power_source_type"] = ""
        formatted_dict["wattage"] = ""
        formatted_dict["special_features1"] = ""
        formatted_dict["special_features2"] = ""
        formatted_dict["special_features3"] = ""
        formatted_dict["special_features4"] = ""
        formatted_dict["special_features5"] = ""
        formatted_dict["pattern_name"] = ""
        formatted_dict["lithium_battery_voltage"] = ""
        formatted_dict["compatible_devices1"] = ""
        formatted_dict["compatible_devices2"] = ""
        formatted_dict["compatible_devices3"] = ""
        formatted_dict["compatible_devices4"] = ""
        formatted_dict["compatible_devices5"] = ""
        formatted_dict["compatible_devices6"] = ""
        formatted_dict["compatible_devices7"] = ""
        formatted_dict["compatible_devices8"] = ""
        formatted_dict["compatible_devices9"] = ""
        formatted_dict["compatible_devices10"] = ""
        formatted_dict["wattage_unit_of_measure"] = ""
        formatted_dict["included_features"] = ""
        formatted_dict["lithium_battery_voltage_unit_of_measure"] = ""
        formatted_dict["length_range"] = ""
        formatted_dict["shaft_style_type"] = ""
        formatted_dict["specification_met"] = ""
        formatted_dict["breed_recommendation"] = ""
        formatted_dict["directions"] = ""
        formatted_dict["number_of_sets"] = ""
        formatted_dict["blade_edge_type"] = ""
        formatted_dict["blade_material_type"] = ""
        formatted_dict["material_composition"] = ""
        formatted_dict["mfg_maximum"] = ""
        formatted_dict["mfg_minimum"] = ""
        formatted_dict["website_shipping_weight"] = ""
        formatted_dict["website_shipping_weight_unit_of_measure"] = ""
        formatted_dict["item_shape"] = ""
        formatted_dict["item_display_length_unit_of_measure"] = ""
        formatted_dict["item_display_width_unit_of_measure"] = ""
        formatted_dict["item_display_height_unit_of_measure"] = ""
        formatted_dict["item_display_length"] = ""
        formatted_dict["item_display_width"] = ""
        formatted_dict["item_display_depth"] = ""
        formatted_dict["item_display_height"] = ""
        formatted_dict["item_display_diameter"] = ""
        formatted_dict["item_display_weight"] = ""
        formatted_dict["item_display_weight_unit_of_measure"] = ""
        formatted_dict["volume_capacity_name"] = 11
        formatted_dict["volume_capacity_name_unit_of_measure"] = "ounces"
        formatted_dict["item_height"] = ""
        formatted_dict["item_length"] = ""
        formatted_dict["item_width"] = ""
        formatted_dict["size_map"] = ""
        formatted_dict["weight_recommendation_unit_of_measure"] = ""
        formatted_dict["width_range"] = ""
        formatted_dict["maximum_weight_recommendation"] = ""
        formatted_dict["item_dimensions_unit_of_measure"] = ""
        formatted_dict["fulfillment_center_id"] = ""
        formatted_dict["package_height"] = ""
        formatted_dict["package_width"] = ""
        formatted_dict["package_length"] = ""
        formatted_dict["package_dimensions_unit_of_measure"] = ""
        formatted_dict["package_weight"] = ""
        formatted_dict["package_weight_unit_of_measure"] = ""
        formatted_dict["energy_efficiency_image_url"] = ""
        formatted_dict["warranty_description"] = ""
        formatted_dict["cpsia_cautionary_statement"] = ""
        formatted_dict["cpsia_cautionary_description"] = ""
        formatted_dict["fabric_type"] = ""
        formatted_dict["import_designation"] = ""
        formatted_dict["legal_compliance_certification_metadata"] = ""
        formatted_dict["legal_compliance_certification_expiration_date"] = ""
        formatted_dict["item_volume"] = ""
        formatted_dict["item_volume_unit_of_measure"] = ""
        formatted_dict["specific_uses_for_product"] = ""
        formatted_dict["country_string"] = ""
        formatted_dict["country_of_origin"] = ""
        formatted_dict["legal_disclaimer_description"] = ""
        formatted_dict["usda_hardiness_zone1"] = ""
        formatted_dict["usda_hardiness_zone2"] = ""
        formatted_dict["are_batteries_included"] = ""
        formatted_dict["item_weight"] = ""
        formatted_dict["batteries_required"] = ""
        formatted_dict["battery_type1"] = ""
        formatted_dict["battery_type2"] = ""
        formatted_dict["battery_type3"] = ""
        formatted_dict["item_weight_unit_of_measure"] = ""
        formatted_dict["number_of_batteries1"] = ""
        formatted_dict["number_of_batteries2"] = ""
        formatted_dict["number_of_batteries3"] = ""
        formatted_dict["lithium_battery_energy_content"] = ""
        formatted_dict["lithium_battery_packaging"] = ""
        formatted_dict["lithium_battery_weight"] = ""
        formatted_dict["number_of_lithium_ion_cells"] = ""
        formatted_dict["number_of_lithium_metal_cells"] = ""
        formatted_dict["battery_cell_composition"] = ""
        formatted_dict["battery_weight"] = ""
        formatted_dict["battery_weight_unit_of_measure"] = ""
        formatted_dict["lithium_battery_energy_content_unit_of_measure"] = ""
        formatted_dict["lithium_battery_weight_unit_of_measure"] = ""
        formatted_dict["supplier_declared_dg_hz_regulation1"] = ""
        formatted_dict["supplier_declared_dg_hz_regulation2"] = ""
        formatted_dict["supplier_declared_dg_hz_regulation3"] = ""
        formatted_dict["supplier_declared_dg_hz_regulation4"] = ""
        formatted_dict["supplier_declared_dg_hz_regulation5"] = ""
        formatted_dict["hazmat_united_nations_regulatory_id"] = ""
        formatted_dict["safety_data_sheet_url"] = ""
        formatted_dict["lighting_facts_image_url"] = ""
        formatted_dict["flash_point"] = ""
        formatted_dict["external_testing_certification1"] = ""
        formatted_dict["external_testing_certification2"] = ""
        formatted_dict["external_testing_certification3"] = ""
        formatted_dict["external_testing_certification4"] = ""
        formatted_dict["external_testing_certification5"] = ""
        formatted_dict["external_testing_certification6"] = ""
        formatted_dict["ghs_classification_class1"] = ""
        formatted_dict["ghs_classification_class2"] = ""
        formatted_dict["ghs_classification_class3"] = ""
        formatted_dict["california_proposition_65_compliance_type"] = ""
        formatted_dict["california_proposition_65_chemical_names1"] = ""
        formatted_dict["california_proposition_65_chemical_names2"] = ""
        formatted_dict["california_proposition_65_chemical_names3"] = ""
        formatted_dict["california_proposition_65_chemical_names4"] = ""
        formatted_dict["california_proposition_65_chemical_names5"] = ""
        formatted_dict["merchant_shipping_group_name"] = ""
        formatted_dict["list_price"] = ""
        formatted_dict["map_price"] = ""
        formatted_dict["product_site_launch_date"] = ""
        formatted_dict["merchant_release_date"] = ""
        formatted_dict["condition_type"] = ""
        formatted_dict["restock_date"] = ""
        formatted_dict["fulfillment_latency"] = ""
        formatted_dict["condition_note"] = ""
        formatted_dict["product_tax_code"] = ""
        formatted_dict["sale_price"] = ""
        formatted_dict["sale_from_date"] = ""
        formatted_dict["sale_end_date"] = ""
        formatted_dict["item_package_quantity"] = ""
        formatted_dict["max_aggregate_ship_quantity"] = ""
        formatted_dict["offering_can_be_gift_messaged"] = ""
        formatted_dict["offering_can_be_giftwrapped"] = ""
        formatted_dict["is_discontinued_by_manufacturer"] = ""
        formatted_dict["max_order_quantity"] = ""
        formatted_dict["number_of_items"] = ""
        formatted_dict["offering_start_date"] = ""
        formatted_dict["offering_end_date"] = ""

        formatted_dicts.append(formatted_dict)

    print("Write listing information to txt file")
    amazon_data = [
        [
            "TemplateType=fptcustom",
            "Version=2020.0324",
            "TemplateSignature=S0lUQ0hFTg==",
            "The top 3 rows are for Amazon.com use only. Do not modify or delete the top 3 rows.",  # noqa:E501
            "",
            "",
            "",
            "",
            "",
            "",
            "Images",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Variation",
            "",
            "",
            "",
            "Basic",
            "",
            "",
            "",
            "",
            "",
            "Discovery",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Product Enrichment",
            "",
            "",
            "",
            "",
            "",
            "Dimensions",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Fulfillment",
            "",
            "",
            "",
            "",
            "",
            "",
            "Compliance",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Offer",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ],
        [
            "Product Type",
            "Seller SKU",
            "Brand Name",
            "Product Name",
            "Product ID",
            "Product ID Type",
            "Item Type Keyword",
            "Standard Price",
            "Quantity",
            "Main Image URL",
            "Other Image URL1",
            "Other Image URL2",
            "Other Image URL3",
            "Other Image URL4",
            "Other Image URL5",
            "Other Image URL6",
            "Other Image URL7",
            "Other Image URL8",
            "Swatch Image URL",
            "Parentage",
            "Parent SKU",
            "Relationship Type",
            "Variation Theme",
            "Update Delete",
            "Product Description",
            "Manufacturer",
            "Manufacturer Part Number",
            "model",
            "closure_type",
            "Key Product Features",
            "Key Product Features",
            "Key Product Features",
            "Key Product Features",
            "Key Product Features",
            "Target Audience",
            "Catalog Number",
            "Used For1 - Used For3",
            "Used For1 - Used For3",
            "Used For1 - Used For3",
            "Used For1 - Used For3",
            "Used For1 - Used For3",
            "Target Audience",
            "Target Audience",
            "Target Audience",
            "Other Attributes",
            "Other Attributes",
            "Other Attributes",
            "Other Attributes",
            "Subject Matter",
            "Subject Matter",
            "Subject Matter",
            "Search Terms",
            "Platinum Keywords",
            "Platinum Keywords",
            "Platinum Keywords",
            "Platinum Keywords",
            "Platinum Keywords",
            "Country/Region as Labeled",
            "Fur Description",
            "Occasion",
            "Number of Pieces",
            "Scent",
            "Included Components",
            "Color",
            "Color Map",
            "Size",
            "Material Type",
            "Style Name",
            "Power Source",
            "Wattage",
            "Additional Features",
            "Additional Features",
            "Additional Features",
            "Additional Features",
            "Additional Features",
            "Pattern",
            "Lithium Battery Voltage",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Compatible Devices",
            "Wattage Unit of Measure",
            "included_features",
            "Lithium Battery Voltage Unit of Measure",
            "Length Range",
            "shaft_style_type",
            "Specification Met",
            "breed_recommendation",
            "directions",
            "Number of Sets",
            "Blade Type",
            "Blade Material Type",
            "Material Composition",
            "Maximum Age Recommendation",
            "Minimum Age Recommendation",
            "Shipping Weight",
            "Website Shipping Weight Unit Of Measure",
            "Shape",
            "Display Length Unit Of Measure",
            "Item Display Width Unit Of Measure",
            "Item Display Height Unit Of Measure",
            "Item Display Length",
            "Item Display Width",
            "Item Display Depth",
            "Item Display Height",
            "Item Display Diameter",
            "Item Display Weight",
            "Item Display Weight Unit Of Measure",
            "Volume",
            "Volume Capacity Name Unit Of Measure",
            "Item Height",
            "Item Length",
            "Item Width",
            "Size Map",
            "Weight Recommendation Unit Of Measure",
            "Width Range",
            "maximum_weight_recommendation",
            "Item Dimensions Unit Of Measure",
            "Fulfillment Center ID",
            "Package Height",
            "Package Width",
            "Package Length",
            "Package Dimensions Unit Of Measure",
            "Package Weight",
            "Package Weight Unit Of Measure",
            "Energy Guide Label",
            "Manufacturer Warranty Description",
            "Cpsia Warning",
            "CPSIA Warning Description",
            "Fabric Type",
            "Import Designation",
            "Please provide the Executive Number (EO) required for sale into California.",  # noqa:E501
            "Please provide the expiration date of the EO Number.",
            "Volume",
            "item_volume_unit_of_measure",
            "Specific Uses For Product",
            "Country/Region of Origin",
            "Country/Region of Origin",
            "Legal Disclaimer",
            "USDA Hardiness Zone",
            "USDA Hardiness Zone",
            "Batteries are Included",
            "Item Weight",
            "Is this product a battery or does it utilize batteries?",
            "Battery type/size",
            "Battery type/size",
            "Battery type/size",
            "item_weight_unit_of_measure",
            "Number of batteries",
            "Number of batteries",
            "Number of batteries",
            "Watt hours per battery",
            "Lithium Battery Packaging",
            "Lithium content (grams)",
            "Number of Lithium-ion Cells",
            "Number of Lithium Metal Cells",
            "Battery composition",
            "Battery weight (grams)",
            "battery_weight_unit_of_measure",
            "lithium_battery_energy_content_unit_of_measure",
            "lithium_battery_weight_unit_of_measure",
            "Applicable Dangerous Goods Regulations",
            "Applicable Dangerous Goods Regulations",
            "Applicable Dangerous Goods Regulations",
            "Applicable Dangerous Goods Regulations",
            "Applicable Dangerous Goods Regulations",
            "UN number",
            "Safety Data Sheet (SDS) URL",
            "Lighting Facts Label",
            "Flash point (°C)?",
            "external_testing_certification1",
            "external_testing_certification2",
            "external_testing_certification3",
            "external_testing_certification4",
            "external_testing_certification5",
            "external_testing_certification6",
            "Categorization/GHS pictograms (select all that apply)",
            "Categorization/GHS pictograms (select all that apply)",
            "Categorization/GHS pictograms (select all that apply)",
            "California Proposition 65 Warning Type",
            "California Proposition 65 Chemical Names",
            "Additional Chemical Name1",
            "Additional Chemical Name2",
            "Additional Chemical Name3",
            "Additional Chemical Name4",
            "Shipping-Template",
            "Manufacturer's Suggested Retail Price",
            "Minimum Advertised Price",
            "Launch Date",
            "Release Date",
            "Item Condition",
            "Restock Date",
            "Handling Time",
            "Offer Condition Note",
            "Product Tax Code",
            "Sale Price",
            "Sale Start Date",
            "Sale End Date",
            "Package Quantity",
            "Max Aggregate Ship Quantity",
            "Offering Can Be Gift Messaged",
            "Is Gift Wrap Available",
            "Is Discontinued by Manufacturer",
            "Max Order Quantity",
            "Number of Items",
            "Offering Release Date",
            "Stop Selling Date"
        ]
    ]
    now_str = datetime.now().strftime("%Y%m%d%H%M")
    keys = formatted_dicts[0].keys()
    with open(f"amazon_data_{now_str}.txt", "w", newline="") as output_file:
        writer = csv.writer(output_file, delimiter="\t")
        writer.writerows(amazon_data)
        dict_writer = csv.DictWriter(output_file, keys, delimiter="\t")
        dict_writer.writeheader()
        dict_writer.writerows(formatted_dicts)


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
    rendered_slogan_dicts = render_mugs(valid_slogan_dicts)
    uploaded_mugs = upload_mugs_to_s3(rendered_slogan_dicts)
    create_amazon_upload_file(uploaded_mugs)
