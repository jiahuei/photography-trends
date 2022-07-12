from __future__ import annotations

import os
from os.path import realpath
from pathlib import Path

import pyexiv2

from utils import io
from utils import metadata as mt

CURR_DIR = Path(realpath(__file__)).parent


def _assert_mssg(metadata, ref_metadata, tag):
    return f"Tag `{tag}` mismatch: metadata={metadata[tag]}   ref_metadata={ref_metadata[tag]}"


def test_metadata():
    metadata_dict = {}
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

                metadata = mt.compile_pyexiv2_metadata(exif_raw, iptc_raw, xmp_raw)
                assert len(metadata) == 12
                metadata_dict[fname] = metadata
    assert len(metadata_dict) == 9

    ref_metadata_list = io.read_json(CURR_DIR / "test_data" / "metadata.json")
    for fname, metadata in metadata_dict.items():
        ref_metadata = ref_metadata_list[fname]
        for tag in ref_metadata.keys():
            if tag == "URL":
                continue
            if tag == "FocalLength":
                assert str(round(metadata[tag])) == ref_metadata[tag], _assert_mssg(
                    metadata, ref_metadata, tag
                )
            elif tag == "FNumber":
                assert f"{metadata[tag]:.1f}" == ref_metadata[tag], _assert_mssg(
                    metadata, ref_metadata, tag
                )
            elif tag == "ExposureTime":
                if "/" in metadata[tag]:
                    assert metadata[tag][:-2] == ref_metadata[tag][:-2], _assert_mssg(
                        metadata, ref_metadata, tag
                    )
                else:
                    assert metadata[tag][:2] == ref_metadata[tag][:2], _assert_mssg(
                        metadata, ref_metadata, tag
                    )
            else:
                assert metadata[tag] == ref_metadata[tag], _assert_mssg(
                    metadata, ref_metadata, tag
                )


if __name__ == "__main__":
    test_metadata()
