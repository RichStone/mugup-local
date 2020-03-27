import asyncio
from asyncio_pool import AioPool
import boto3
import csv
from datetime import date
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


async def main(*, infolder, bucket):
    AWS_ACCESS_KEY_ID = "AKIAINCEUCJHE3FHXWBQ"
    AWS_SECRET_ACCESS_KEY = "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"

    def render_multiple_mockups(*, img_list, infolder):
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
            new_img_name = f"{img_name_no_extension}_r.png"

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
                s3.upload_fileobj(f, bucket, s3_img_path)
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
                s3.upload_fileobj(f, bucket, s3_img_path)
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

    img_list_initial = glob(os.path.join(infolder, "*"))
    if platform == "win32":
        img_list = []
        for img_str in img_list_initial:
            updated_img_str = img_str.replace("\\\\", "\\")
            img_list.append(updated_img_str)
    elif platform == "darwin":
        img_list = img_list_initial

    print(f"Render slogan files and upload to S3 bucket {bucket}")
    img_urls = render_multiple_mockups(
        img_list=img_list,
        infolder=infolder,
    )

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
    for img_dict in progressbar(img_dicts_with_crop):
        formatted_dict = {}

        formatted_dict["main-image-url"] = img_dict["left_url_cropped"]
        formatted_dict["other-image-url1"] = img_dict["right_url_cropped"]
        formatted_dict["other-image-url2"] = img_dict["on_board_url"]
        formatted_dict["other-image-url3"] = img_dict["lady_example_url"]
        formatted_dict["other-image-url4"] = img_dict["pen_example_url"]
        formatted_dict["other-image-url5"] = img_dict["microwave_safe_url"]
        formatted_dict["other-image-url6"] = img_dict["four_fingers_example"]

        formatted_dicts.append(formatted_dict)

    print("Write mockup URLs to csv")
    keys = formatted_dicts[0].keys()
    with open("image_urls.csv", "w", newline="") as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(formatted_dicts)


if __name__ == "__main__":
    asyncio.run(main())
