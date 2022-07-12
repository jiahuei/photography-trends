from __future__ import annotations

from typing import Any

import PIL

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
}


def compile_metadata(exif: dict, iptc: dict, xmp: dict):
    metadata = {}
    for tag, tag_raw in EXIF_TAGS_MAP.items():
        metadata[tag] = exif[tag_raw]
    for tag, tag_raw in EXIF_EXTRA_TAGS_MAP.items():
        metadata[tag] = exif.get(tag_raw, xmp.get(XMP_TAGS_MAP.get(tag, None), "NA"))
    return metadata


def to_float(x: Any):
    if isinstance(x, PIL.TiffImagePlugin.IFDRational):
        if x.denominator == 0:
            x = x.numerator / 1e-3
        else:
            x = x.numerator / x.denominator
    return x


def print_exif_data(exif_data: dict):
    for tag, content in exif_data.items():
        print(f"{tag:25}: {content}")
