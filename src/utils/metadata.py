from __future__ import annotations

from datetime import datetime
from typing import Any

import PIL
import pyexiv2
from PIL import TiffImagePlugin

pyexiv2.enableBMFF()

EXIF_TAGS_MAP = {
    "DateTimeOriginal": "Exif.Photo.DateTimeOriginal",
    "ExposureTime": "Exif.Photo.ExposureTime",
    "ShutterSpeedValue": "Exif.Photo.ShutterSpeedValue",
    "FNumber": "Exif.Photo.FNumber",
    "FocalLength": "Exif.Photo.FocalLength",
    "ISOSpeedRatings": "Exif.Photo.ISOSpeedRatings",
}

EXIF_EXTRA_TAGS_MAP = {
    "LensModel": "Exif.Photo.LensModel",
    "CameraModel": "Exif.Image.Model",
    "Width": "Exif.Photo.PixelXDimension",
    "Height": "Exif.Photo.PixelYDimension",
}

XMP_TAGS_MAP = {
    "LensModel": "Xmp.aux.Lens",
    "CameraModel": "Xmp.tiff.Model",
    "CreatorTool": "CreatorTool",
}


def compile_metadata(exif: dict, iptc: dict, xmp: dict):
    metadata = {}
    for tag, tag_raw in EXIF_TAGS_MAP.items():
        metadata[tag] = exif[tag_raw]
    extra_tags = set(list(EXIF_EXTRA_TAGS_MAP.keys()) + list(XMP_TAGS_MAP.keys()))
    for tag in extra_tags:
        metadata[tag] = exif.get(
            EXIF_EXTRA_TAGS_MAP.get(tag, None),
            xmp.get(XMP_TAGS_MAP.get(tag, None), "NA"),
        )
    metadata["ShutterSpeedValue"] = to_float(metadata["ShutterSpeedValue"].split("/"))
    metadata["FNumber"] = to_float(metadata["FNumber"].split("/"))
    metadata["FocalLength"] = to_float(metadata["FocalLength"].split("/"))
    try:
        metadata["DateTimeOriginal"] = datetime.strptime(
            metadata["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S"
        )
    except (KeyError, ValueError):
        metadata["DateTimeOriginal"] = datetime.min
    return metadata


def extract_metadata(file_path: str):
    with pyexiv2.Image(str(file_path)) as img:
        exif_raw = img.read_exif()
        iptc_raw = img.read_iptc()
        xmp_raw = img.read_xmp()

    xmp_raw["CreatorTool"] = "NA"
    try:
        with PIL.Image.open(file_path) as img:
            try:
                xmp2 = img.getxmp()
                print(xmp2)
                desc = xmp2["xmpmeta"]["RDF"]["Description"]
            except (KeyError, TypeError):
                xmp_raw["CreatorTool"] = "NA"
            else:
                if isinstance(desc, list):
                    for d in desc:
                        xmp_raw["CreatorTool"] = d.get("CreatorTool", xmp_raw.get("CreatorTool"))
                elif isinstance(desc, dict):
                    xmp_raw["CreatorTool"] = desc.get("CreatorTool", "NA")
                else:
                    xmp_raw["CreatorTool"] = "NA"
    except PIL.UnidentifiedImageError:
        pass
    return compile_metadata(exif_raw, iptc_raw, xmp_raw)


def to_float(x: Any):
    if isinstance(x, TiffImagePlugin.IFDRational):
        if x.denominator == 0:
            x = x.numerator / 1e-3
        else:
            x = x.numerator / x.denominator
    elif isinstance(x, (tuple, list)):
        assert len(x) == 2
        x = tuple(map(float, x))
        if x[1] == 0:
            x = x[0] / 1e-3
        else:
            x = x[0] / x[1]
    return x


def print_exif_data(exif_data: dict):
    for tag, content in exif_data.items():
        print(f"{tag:25}: {content}")