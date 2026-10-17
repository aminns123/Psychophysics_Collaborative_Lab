"""Run with USER_env Python: python -m examples.shared_stimuli --output NEW_FOLDER."""
import argparse
import json
from pathlib import Path
import numpy as np
from matplotlib import pyplot as plt
from psychophysics_lab.stimulus_library import (
    Scene, fixation, line, rectangle, square, grating, gabor, ellipse, annulus, gaussian_dot,
)


def preview(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    drawings = [fixation(), line(), rectangle(width_deg=.4,height_deg=1.), square(),
                grating(size_deg=2), gabor(size_deg=2,sigma_deg=.3), ellipse(), annulus(), gaussian_dot(sigma_deg=.15)]
    labels = ["Fixation", "Line", "Rectangle", "Square", "Grating", "Gabor", "Ellipse", "Annulus", "Gaussian dot"]
    grid = (np.arange(512)+.5-256)*3/512
    x,y = np.meshgrid(grid,grid)
    fig,axes = plt.subplots(3,3,figsize=(9,9),layout="constrained")
    for ax,drawing,label in zip(axes.flat,drawings,labels):
        ax.imshow(Scene(drawing).render(x,y),origin="lower",extent=(-1.5,1.5,-1.5,1.5),cmap="gray",vmin=0,vmax=1)
        ax.set_title(label); ax.set_xlabel("degrees"); ax.set_ylabel("degrees")
    fig.suptitle("PsyCoLab shared drawings — digital previews")
    fig.savefig(output/"primitives.png",dpi=130)
    plt.close(fig)
    scene = Scene(grating(size_deg=2, x_deg=-2, amplitude=.09),
                  annulus(radius_x_deg=.8,radius_y_deg=.55,x_deg=2),
                  fixation(),line(length_deg=.4,width_deg=.06,x_deg=2,y_deg=.6))
    (output/"scene.json").write_text(json.dumps(scene.to_dict(),indent=2)+"\n")
    grid = (np.arange(1024)+.5-512)*8/1024
    x,y = np.meshgrid(grid,grid)
    fig,ax = plt.subplots(figsize=(10,6),layout="constrained")
    ax.imshow(scene.render(x,y),origin="lower",extent=(-4,4,-4,4),cmap="gray",vmin=0,vmax=1)
    ax.set(xlabel="degrees",ylabel="degrees",title="Compose independent drawings on one background")
    fig.savefig(output/"composition.png",dpi=130)
    plt.close(fig)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    print(preview(parser.parse_args().output))
