from __future__ import annotations

import os
from os.path import realpath
from pathlib import Path

import pyexiv2

from utils import io
from utils import metadata as mt

CURR_DIR = Path(realpath(__file__)).parent
pyexiv2.enableBMFF()


def test_metadata():
    metadata_list = []
    for root, _, files in os.walk(CURR_DIR / "test_data", topdown=False):
        root = Path(root)
        for fname in sorted(files):
            if not (io.is_jpg(fname) or io.is_raw(fname)):
                continue
            fpath = root / fname
            with pyexiv2.Image(str(fpath)) as img:
                exif_raw = img.read_exif()
                iptc_raw = img.read_iptc()
                xmp_raw = img.read_xmp()
                assert isinstance(exif_raw, dict)
                assert isinstance(iptc_raw, dict)
                assert isinstance(xmp_raw, dict)

                for tag_raw in mt.EXIF_TAGS_MAP.values():
                    assert tag_raw in exif_raw, f"Tag {tag_raw} missing from: {fname}"

                metadata = mt.compile_metadata(exif_raw, iptc_raw, xmp_raw)
                assert len(metadata) == 11
                metadata_list.append(metadata)
    assert len(metadata_list) == 5


if __name__ == "__main__":
    test_metadata()
