# -*- coding: utf-8 -*-
"""
Created on 04 July 2022
@author: jiahuei
"""
from __future__ import annotations

import argparse
import math
import os
from os.path import dirname, join, realpath

import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from tqdm import tqdm

from utils import io
from utils import metadata as mt

sns.set_theme(
    style="whitegrid",
    rc={
        "axes.edgecolor": ".3",
        "grid.color": "0.9",  # "axes.grid.axis": "y",
        "legend.loc": "lower left",
        "legend.framealpha": "0.6",
    },
)
CURR_DIR = dirname(realpath(__file__))


def extract_array(metadata_list: list[dict], key: str, default=0.0):
    return np.array([m.get(key, default) for m in metadata_list])


def plot(
    data,
    title,
    ax,
    xticks=None,
    xticklabels=None,
    **plot_kwargs,
):
    ax = sns.histplot(data, ax=ax, **plot_kwargs)
    ax.set_title(title, pad=plt.rcParams["font.size"] * 1.5)

    for p in ax.patches:
        h = p.get_height()
        h = f"{h:,d}" if h > 0 else ""
        ax.annotate(
            h,
            (p.get_x() + p.get_width() / 2.0, p.get_height()),
            ha="center",
            va="center",
            fontsize="xx-small",
            color="gray",
            xytext=(0, 5),
            textcoords="offset points",
        )

    if xticks is not None and xticklabels is not None:
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)

    ax.tick_params(axis="x", labelrotation=90, labelsize="xx-small")


def plot_all(metadata_list, output_name, save_memory: bool = False):
    tqdm.write(f"Plotting chart: {output_name}")

    f_lens = extract_array(metadata_list, "FocalLength").astype(np.float64)
    f_nums = extract_array(metadata_list, "FNumber").astype(np.float64)
    lens_models = extract_array(metadata_list, "LensModel", "NA")
    iso_nums = extract_array(metadata_list, "ISOSpeedRatings").astype(np.float64)
    shutter_speed = extract_array(metadata_list, "ShutterSpeedValue", 16.0)
    assert len(f_lens) > 0

    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=[16.0, 8.0], constrained_layout=True)
    # Focal lengths
    plot(f_lens, "Focal Length Distribution", axes[0, 0])

    # F-stop
    plot(f_nums, "F-stop Distribution", axes[0, 1])

    # ISOs
    iso_log = np.log2(iso_nums)
    xticks = list(range(math.floor(iso_log.min()) - 1, math.ceil(iso_log.max()) + 1))
    xticklabels = [f"{round(2.0 ** x):,d}" for x in xticks]
    plot(iso_log, "ISO Distribution", axes[0, 2], xticks=xticks, xticklabels=xticklabels)

    # Exposure times
    if not save_memory:
        ss_max = math.ceil(shutter_speed.max()) + 1
        ss_min = math.floor(shutter_speed.min()) - 1
        xticks = list(range(ss_min, ss_max))
        xticklabels = [mt.convert_shutter_value(x, True) for x in xticks]
        plot(
            shutter_speed,
            "Shutter Speed Distribution",
            axes[1, 0],
            xticks=xticks,
            xticklabels=xticklabels,
        )

    # Lens models
    plot(lens_models, "Lens Model Distribution", axes[1, 2])

    fig.suptitle(output_name, fontsize="large")

    os.makedirs(join(CURR_DIR, "plots"), exist_ok=True)
    plt.savefig(join(CURR_DIR, "plots", output_name), dpi=600)  # , plt.show()
    plt.clf()
    plt.close("all")


def main(
    dir_path: str,
    original_only: bool,
    processed_only: bool,
    save_memory: bool = False,
    read_jpg: bool = False,
):
    if not read_jpg and (original_only or processed_only):
        tqdm.write(
            "`original_only` and `processed_only` cannot be True if `read_jpg` is False. Exiting ..."
        )
        exit(1)

    if original_only and processed_only:
        tqdm.write("`original_only` and `processed_only` cannot both be True. Exiting ...")
        exit(1)

    # List image files
    file_filter_fn = io.is_jpg if read_jpg else io.is_raw
    img_files = []
    for root, _, files in os.walk(dir_path, topdown=False):
        for fname in sorted(files):
            if not file_filter_fn(fname):
                continue
            fpath = os.path.join(root, fname)
            img_files.append(fpath)

    metadata_list = []
    for fpath in tqdm(img_files, "Reading EXIF data"):
        metadata = mt.extract_metadata(fpath)
        if "FocalLength" not in metadata:
            tqdm.write(f"Focal length data missing: {fpath}")
            continue
        if original_only and metadata["CreatorTool"] != "NA":
            tqdm.write(f"This seems like a processed image: {fpath}")
            continue
        if processed_only and metadata["CreatorTool"] in ("NA", "Unknown"):
            tqdm.write(f"This seems like an unprocessed image: {fpath}")
            continue
        metadata_list.append(metadata)
    mt.print_exif_data(metadata_list[0])

    # Plot combined
    plot_all(metadata_list, "Photo Trend - All", save_memory)

    # Per year
    years = set([m["DateTimeOriginal"].year for m in metadata_list])
    for year in sorted(years):
        plot_all(
            [m for m in metadata_list if m["DateTimeOriginal"].year == year],
            f"Photo Trend - {year:04d}",
            save_memory,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--dir_path",
        "-d",
        type=str,
        help="str: Path to the experiment logging directory.",
    )
    parser.add_argument(
        "--save_memory",
        "-m",
        action="store_true",
        help="bool: If specified, plot fewer charts to reduce memory usage.",
    )
    parser.add_argument(
        "--read_jpg",
        "-j",
        action="store_true",
        help="bool: If specified, only analyse JPEG images.",
    )
    parser.add_argument(
        "--original_only",
        "-oo",
        action="store_true",
        help="bool: If specified, only analyse original unprocessed images.",
    )
    parser.add_argument(
        "--processed_only",
        "-po",
        action="store_true",
        help="bool: If specified, only analyse processed images.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main(**vars(parse_args()))
