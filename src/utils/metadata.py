from __future__ import annotations

import string
from datetime import datetime
from typing import Any

import numpy as np
import PIL
import pyexiv2
from PIL import ExifTags, TiffImagePlugin

pyexiv2.enableBMFF()
ASCII_LOWERCASE = set(string.ascii_lowercase)

PIL_EXIF_TAGS = [
    "DateTimeOriginal",
    "ExposureTime",
    "ShutterSpeedValue",
    "FNumber",
    "FocalLength",
    "ISOSpeedRatings",
    "LensModel",
    "CameraModel",
]

EXIF_TAGS_MAP = {
    "DateTimeOriginal": "Exif.Photo.DateTimeOriginal",
    "ExposureTimeRaw": "Exif.Photo.ExposureTime",
    "FNumber": "Exif.Photo.FNumber",
    "FocalLength": "Exif.Photo.FocalLength",
    "ISOSpeedRatings": "Exif.Photo.ISOSpeedRatings",
}

EXIF_EXTRA_TAGS_MAP = {
    "ShutterSpeedValueRaw": "Exif.Photo.ShutterSpeedValue",
    "LensModel": "Exif.Photo.LensModel",
    "CameraModel": "Exif.Image.Model",
    "Width": "Exif.Photo.PixelXDimension",
    "Height": "Exif.Photo.PixelYDimension",
}

XMP_TAGS_MAP = {
    "LensModel": "Xmp.aux.Lens",
    "CameraModel": "Xmp.tiff.Model",
}


def compile_pyexiv2_metadata(exif: dict, iptc: dict, xmp: dict):
    metadata = {}
    for tag, tag_raw in EXIF_TAGS_MAP.items():
        metadata[tag] = exif[tag_raw]
    extra_tags = set(list(EXIF_EXTRA_TAGS_MAP.keys()) + list(XMP_TAGS_MAP.keys()))
    for tag in extra_tags:
        metadata[tag] = exif.get(
            EXIF_EXTRA_TAGS_MAP.get(tag, None),
            xmp.get(XMP_TAGS_MAP.get(tag, None), "NA"),
        )
    et = tuple(map(float, metadata["ExposureTimeRaw"].split("/")))
    metadata["ShutterSpeedValue"] = np.log2(et[1] / et[0])
    metadata["ExposureTime"] = convert_shutter_value(metadata["ShutterSpeedValue"])
    metadata["FNumber"] = to_float(metadata["FNumber"].split("/"))
    metadata["FocalLength"] = to_float(metadata["FocalLength"].split("/"))
    metadata["DateTimeOriginal"] = convert_datetime(metadata["DateTimeOriginal"])
    metadata["LensModel"] = cleanup_name(metadata.get("LensModel", "NA"))
    metadata["CameraModel"] = cleanup_name(metadata.get("CameraModel", "NA"))
    return metadata


def extract_metadata(file_path: str):
    metadata = {"FilePath": file_path}
    try:
        with PIL.Image.open(file_path) as img:
            exif = img.getexif().get_ifd(0x8769)
            exif = {ExifTags.TAGS.get(tag_id, tag_id): exif.get(tag_id) for tag_id in exif}
            metadata.update({tag: to_float(exif.get(tag)) for tag in PIL_EXIF_TAGS})
            metadata["CreatorTool"] = "NA"
            try:
                xmp2 = img.getxmp()
                desc = xmp2["xmpmeta"]["RDF"]["Description"]
            except (KeyError, TypeError):
                pass
            else:
                if isinstance(desc, list):
                    for d in desc:
                        metadata["CreatorTool"] = d.get("CreatorTool", metadata.get("CreatorTool"))
                elif isinstance(desc, dict):
                    metadata["CreatorTool"] = desc.get("CreatorTool", metadata.get("CreatorTool"))
                else:
                    pass
        metadata["DateTimeOriginal"] = convert_datetime(metadata["DateTimeOriginal"])
        metadata["LensModel"] = cleanup_name(metadata.get("LensModel", "NA"))
        metadata["CameraModel"] = cleanup_name(metadata.get("CameraModel", "NA"))
    except (PIL.UnidentifiedImageError, AssertionError):
        pass
    else:
        return metadata
    try:
        with pyexiv2.Image(str(file_path)) as img:
            exif_raw = img.read_exif()
            iptc_raw = img.read_iptc()
            xmp_raw = img.read_xmp()
        metadata.update(compile_pyexiv2_metadata(exif_raw, iptc_raw, xmp_raw))
    except (RuntimeError, AssertionError):
        pass
    return metadata


def convert_datetime(x: str) -> datetime:
    try:
        x = datetime.strptime(x, "%Y:%m:%d %H:%M:%S")
    except (KeyError, ValueError):
        x = datetime.min
    return x


def convert_shutter_value(x: float, thousand_sep: bool = False) -> str:
    if x > 0:
        x = round(1.0 / (2.0 ** (-x)))
        return f"1/{x:,d}" if thousand_sep else f"1/{x:d}"
    else:
        x = round(2.0 ** (-x))
        return f"{x:,d}" if thousand_sep else str(x)


def cleanup_name(x: str | None) -> str:
    if x is None:
        x = "NA"
    x = x.encode("ascii", errors="ignore").decode()
    if not any(c in ASCII_LOWERCASE for c in x.lower()):
        x = "NA"
    return x


def to_float(x: Any) -> Any:
    if isinstance(x, TiffImagePlugin.IFDRational):
        if x.denominator == 0:
            x = x.numerator / 1e-3
        else:
            x = x.numerator / x.denominator
    elif isinstance(x, (tuple, list)):
        assert len(x) == 2, f"`to_float()` input must be len 2, received: {x}"
        x = tuple(map(float, x))
        if x[1] == 0:
            x = x[0] / 1e-3
        else:
            x = x[0] / x[1]
    return x


def print_exif_data(exif_data: dict) -> None:
    for tag, content in exif_data.items():
        print(f"{tag:25}: {content}")
