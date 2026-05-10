#!/usr/bin/env python3
"""Display or save a 2D image from a FITS map."""

from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot a 2D FITS map, using WCS coordinates when available."
    )
    parser.add_argument(
        "fits_file",
        help="Path to the FITS file.",
    )
    parser.add_argument("--hdu", type=int, default=0, help="HDU index to read.")
    parser.add_argument(
        "--plane",
        type=int,
        default=0,
        help=(
            "Plane index to plot if the FITS data has more than two dimensions "
            "after squeezing."
        ),
    )
    parser.add_argument(
        "--mk-units",
        action="store_true",
        help="Convert map values from K to mK before plotting.",
    )
    parser.add_argument(
        "--vmin",
        type=float,
        default=None,
        help="Minimum colormap value. Defaults to percentile clipping.",
    )
    parser.add_argument(
        "--vmax",
        type=float,
        default=None,
        help="Maximum colormap value. Defaults to percentile clipping.",
    )
    parser.add_argument(
        "--percentile",
        type=float,
        nargs=2,
        default=(1.0, 99.0),
        metavar=("LOW", "HIGH"),
        help="Percentiles used for vmin/vmax when either is omitted.",
    )
    parser.add_argument("--cmap", default="plasma", help="Matplotlib colormap name.")
    parser.add_argument("--title", default=None, help="Optional plot title.")
    parser.add_argument(
        "--colorbar-label",
        default="Intensity",
        help="Label for the colorbar.",
    )
    parser.add_argument(
        "--no-wcs",
        action="store_true",
        help="Plot in pixel coordinates instead of FITS WCS coordinates.",
    )
    parser.add_argument(
        "--save",
        default=None,
        help=(
            "Output image path. Defaults to the FITS path with the suffix changed "
            "to .png."
        ),
    )
    return parser.parse_args()


def import_plotting_dependencies():
    from astropy.io import fits
    from astropy.wcs import WCS
    import matplotlib
    import matplotlib.pyplot as plt
    return fits, WCS, plt
    matplotlib.use("Agg")

def select_2d_plane(data: np.ndarray, plane: int) -> np.ndarray:
    image = np.asarray(data).squeeze()

    if image.ndim == 2:
        return image

    if image.ndim < 2:
        raise ValueError(f"Expected at least 2D FITS data, got shape {image.shape}")

    leading_shape = image.shape[:-2]
    n_planes = int(np.prod(leading_shape))
    if plane < 0 or plane >= n_planes:
        raise ValueError(
            f"--plane must be between 0 and {n_planes - 1} for data shape {image.shape}"
        )

    return image.reshape((n_planes,) + image.shape[-2:])[plane]


def finite_limits(image: np.ndarray, percentile: tuple[float, float]) -> tuple[float, float]:
    finite = image[np.isfinite(image)]
    if finite.size == 0:
        raise ValueError("No finite pixels found to plot.")
    return tuple(np.nanpercentile(finite, percentile))


def main() -> None:
    args = parse_args()
    fits, WCS, plt = import_plotting_dependencies()

    fits_path = Path(args.fits_file)
    with fits.open(fits_path) as hdul:
        hdu = hdul[args.hdu]
        if hdu.data is None:
            raise ValueError(f"HDU {args.hdu} in {fits_path} has no image data.")

        image = select_2d_plane(hdu.data, args.plane).astype(float, copy=False)
        if args.mk_units:
            image = image * 1000.0
        image = image.copy()
        image[image == 0] = np.nan

        header = hdu.header.copy()

    auto_vmin, auto_vmax = finite_limits(image, tuple(args.percentile))
    vmin = args.vmin if args.vmin is not None else auto_vmin
    vmax = args.vmax if args.vmax is not None else auto_vmax

    projection = None if args.no_wcs else WCS(header).celestial
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection=projection)
    cmap = plt.get_cmap(args.cmap).copy()
    cmap.set_bad("lightgray")

    im = ax.imshow(
        image,
        origin="lower",
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
    )

    if projection is None:
        ax.set_xlabel("X pixel")
        ax.set_ylabel("Y pixel")
    else:
        ax.set_xlabel("RA (deg)")
        ax.set_ylabel("Dec (deg)")
        ax.coords[0].set_format_unit("deg", decimal=True)
        ax.coords[1].set_format_unit("deg", decimal=True)
        ax.coords.grid(color="white", alpha=0.35, linestyle=":", linewidth=0.8)

    title = args.title if args.title is not None else fits_path.name
    ax.set_title(title)

    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    colorbar_label = (
        f"{args.colorbar_label} [mK]" if args.mk_units else args.colorbar_label
    )
    cbar.set_label(colorbar_label)
    fig.tight_layout()

    save_path = Path(args.save) if args.save else fits_path.with_suffix(".png")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, bbox_inches="tight")
    print(f"Saved {save_path}")

if __name__ == "__main__":
    main()
