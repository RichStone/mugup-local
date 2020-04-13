import asyncio
from asyncio_pool import AioPool
import boto3
import csv
from datetime import date, datetime
from glob import glob
import httpx
from io import BytesIO
import json
import os
import pdb
from pathlib import Path
from PIL import Image
from progressbar import progressbar
from shutil import rmtree
from sys import platform


async def main(*, infolder, bucket, slogan_inputs):
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    def render_multiple_mockups(img_list):
        """
        Given a list of PNG images, renders and exports those images
        in 3200 x 1050 format to be ready for upload to Printful.
        """
        def render_mockup_ready_slogan_image(img_name):
            if platform == "darwin":
                img_no_folder = img_name.replace(f"{infolder}/", "")
            elif platform == "win32":
                img_no_folder = img_name.replace(f"{infolder}\\", "")
            img_name_no_extension = img_no_folder.split(".png")[0]
            img = Image.open(img_name, "r")
            background = Image.new("RGBA", (2500, 1050), (255, 255, 255, 255))
            background.paste(img, (70, 105))
            background.paste(img, (1440, 105))
            new_img_name = f"{img_name_no_extension}.png"

            new_img_path = Path(f"{write_directory}/{new_img_name}")
            background.save(new_img_path)
            return new_img_path

        # Check if directory exists for writing
        # https://stackoverflow.com/a/273227/1723469
        write_directory = "temp"
        Path(write_directory).mkdir(parents=True, exist_ok=True)
        today_str = str(date.today())

        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        img_urls = []
        for img in progressbar(img_list):
            try:
                new_img_path = render_mockup_ready_slogan_image(img)
                if platform == "win32":
                    new_img_name = str(new_img_path).split("\\")[-1]
                elif platform == "darwin":
                    new_img_name = str(new_img_path).split("/")[-1]
                s3_img_path = f"{today_str}/{new_img_name}"
                with open(new_img_path, "rb") as f:
                    s3.upload_fileobj(f, bucket, s3_img_path)

                # Example finished AWS S3 URL
                # https://giftsondemand.s3.amazonaws.com/2020-01-07/10_r.png
                aws_url = f"https://{bucket}.s3.amazonaws.com/{s3_img_path}"
                img_urls.append(aws_url)
            except Exception as e:
                print(e)
                pdb.set_trace()

        rmtree(write_directory)

        return img_urls

    async def crop_main_images(img_dicts):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        write_directory = "temp"

        async def crop_left(img_dict):
            s3_img_url = img_dict["handle_left_url"]
            async with httpx.AsyncClient() as client:
                img_resp = await client.get(s3_img_url)
            img = Image.open(BytesIO(img_resp.content))

            # Crop
            start_x = 110
            start_y = 270
            end_x = 740
            end_y = 830
            cropped = img.crop((start_x, start_y, end_x, end_y))

            # Enlarge
            enlarged_size = (1136, 1010)
            crop_enlarged = cropped.resize(enlarged_size)

            # Save
            new_img_name = f"{img_dict['name']}_left_crop.png"
            new_img_path = f"{write_directory}/{new_img_name}"
            crop_enlarged.save(new_img_path)

            # Upload to s3
            s3_img_path = f"left_handle/{new_img_name}"
            with open(new_img_path, "rb") as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=s3_img_path,
                    Body=f,
                    ContentType="image/png",
                    ACL="public-read"
                )
            aws_url = f"https://{bucket}.s3.amazonaws.com/{s3_img_path}"
            return aws_url

        async def crop_right(img_dict):
            s3_img_url = img_dict["handle_right_url"]
            async with httpx.AsyncClient() as client:
                img_resp = await client.get(s3_img_url)
            img = Image.open(BytesIO(img_resp.content))

            # Crop
            start_x = 250
            start_y = 270
            end_x = 860
            end_y = 830
            cropped = img.crop((start_x, start_y, end_x, end_y))

            # Enlarge
            enlarged_size = (1136, 1010)
            crop_enlarged = cropped.resize(enlarged_size)

            # Save
            new_img_name = f"{img_dict['name']}_right_crop.png"
            new_img_path = f"{write_directory}/{new_img_name}"
            crop_enlarged.save(new_img_path)

            # Upload to s3
            s3_img_path = f"right_handle/{new_img_name}"
            with open(new_img_path, "rb") as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=s3_img_path,
                    Body=f,
                    ContentType="image/png",
                    ACL="public-read"
                )
            aws_url = f"https://{bucket}.s3.amazonaws.com/{s3_img_path}"
            return aws_url

            # Check if directory exists for writing
            # https://stackoverflow.com/a/273227/1723469
            Path(write_directory).mkdir(parents=True, exist_ok=True)

            for img_dict in progressbar(img_dicts):
                try:
                    img_dict["left_url_cropped"] = await crop_left(img_dict)
                    img_dict["right_url_cropped"] = await crop_right(img_dict)
                except Exception as e:
                    print(e)
                    pdb.set_trace()

            rmtree(write_directory)

            return img_dicts

        # Check if directory exists for writing
        # https://stackoverflow.com/a/273227/1723469
        write_directory = "temp"
        Path(write_directory).mkdir(parents=True, exist_ok=True)
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

        for img_dict in progressbar(img_dicts):
            try:
                img_dict["left_url_cropped"] = await crop_left(img_dict)
                img_dict["right_url_cropped"] = await crop_right(img_dict)
            except Exception as e:
                print(e)
                pdb.set_trace()

        rmtree(write_directory)

        return img_dicts

    async def render_11oz_mug_mockup(img_url):
        """
        Using a hosted image render an 11oz mug mockup
        Docs here https://www.printful.com/docs/generator
        """
        mock_gen_url = "https://api.printful.com/mockup-generator/create-task/19"

        mock_gen_payload = {
            "variant_ids": [1320],
            "format": "jpg",
            "files": [
                {
                    "placement": "default",
                    "image_url": img_url,
                    "position":
                    {
                        "area_width": 2500,
                        "area_height": 1050,
                        "width": 2500,
                        "height": 1050,
                        "top": 0,
                        "left": 0
                    }
                }
            ]
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic eGlobWt1aHItbnI4dy16NG5nOjVvY20tMTR5YmRveGZ2a3M5"  # noqa:E501
        }

        async with httpx.AsyncClient() as client:
            mock_gen_resp = await client.post(
                mock_gen_url,
                headers=headers,
                json=mock_gen_payload
            )

        mock_gen_json = json.loads(mock_gen_resp.text)

        task_key = mock_gen_json["result"]["task_key"]

        await asyncio.sleep(20)

        finished_mock_url = "https://api.printful.com/mockup-generator/task"

        finished_mock_params = {
            "task_key": task_key
        }

        async with httpx.AsyncClient() as client:
            finished_mock_resp = await client.get(
                finished_mock_url,
                headers=headers,
                params=finished_mock_params
            )

        mock_json = json.loads(finished_mock_resp.text)

        mockup_urls_dict = {}
        handle_right_url = mock_json["result"]["mockups"][0]["mockup_url"]
        handle_left_url = mock_json["result"]["mockups"][0]["extra"][0]["url"]
        on_board_url = mock_json["result"]["mockups"][0]["extra"][6]["url"]

        # Generate name from file path.  8_r is the name for
        # https://giftsondemand.s3.amazonaws.com/2020-01-07/8_r.png
        mockup_urls_dict["name"] = img_url.split(".")[-2].split("/")[-1]
        mockup_urls_dict["handle_right_url"] = handle_right_url
        mockup_urls_dict["handle_left_url"] = handle_left_url
        mockup_urls_dict["on_board_url"] = on_board_url

        return mockup_urls_dict

    def match_slogan_input_with_image(img_dict, slogan_inputs):
        for i, slogan_dict in enumerate(slogan_inputs):
            if slogan_dict["name"] == img_dict["name"]:
                matched_slogan_row = i
                break
        try:
            matched_slogan_dict = slogan_inputs[matched_slogan_row]
            return matched_slogan_dict
        except NameError:
            pdb.set_trace()

    img_list_initial = glob(os.path.join(infolder, "*"))
    if platform == "win32":
        img_list = []
        for img_str in img_list_initial:
            updated_img_str = img_str.replace("\\\\", "\\")
            img_list.append(updated_img_str)
    elif platform == "darwin":
        img_list = img_list_initial

    print(f"Render slogan files and upload to S3 bucket {bucket}")
    img_urls = render_multiple_mockups(img_list)

    print("Render Printful mockups")
    pool = AioPool(size=3)
    mockup_img_dicts = await pool.map(
        render_11oz_mug_mockup,
        progressbar(img_urls)
    )

    print("Crop main images")
    img_dicts_with_crop = await crop_main_images(mockup_img_dicts)

    print("Add static images")
    for img_dict in progressbar(img_dicts_with_crop):
        base_url = "https://giftsondemand.s3.amazonaws.com/static"

        img_dict["lady_example_url"] = f"{base_url}/woman_mug.jpg"
        img_dict["pen_example_url"] = f"{base_url}/mug_with_pens.jpg"
        img_dict["microwave_safe_url"] = f"{base_url}/microwave_safe.jpg"
        img_dict["four_fingers_example"] = f"{base_url}/four_fingers.jpg"

    print("Format dict for csv printing")
    formatted_dicts = []
    today_str = date.today().strftime("%Y%m%d")

    for i, img_dict in progressbar(enumerate(img_dicts_with_crop)):
        slogan_dict = match_slogan_input_with_image(img_dict, slogan_inputs)
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
        formatted_dict["main-image-url"] = img_dict["left_url_cropped"]
        formatted_dict["other-image-url1"] = img_dict["right_url_cropped"]
        formatted_dict["other-image-url2"] = img_dict["on_board_url"]
        formatted_dict["other-image-url3"] = img_dict["lady_example_url"]
        formatted_dict["other-image-url4"] = img_dict["pen_example_url"]
        formatted_dict["other-image-url5"] = img_dict["microwave_safe_url"]
        formatted_dict["other-image-url6"] = img_dict["four_fingers_example"]
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
    asyncio.run(main())
