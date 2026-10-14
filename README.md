# About

This lets you unpack the sfai file that contains all of the data from Darkfall or Darkfall: Unholy Wars.
I didn't write the original code, I just fixed it up to work with UW.
It also contains scripts for converting models. I've successfully used this to import DF models and sounds in to other games before.

## Things working:
* Static models
* Textures
* Sounds
* XML files
* Maps (levels), terrain tiles, collision (AABB trees + shapes), skinned models in bind pose -- see below

## Things not working:
* Animation tracks in `.sfas` (the per-bone channel layout is partly understood, see `FORMATS.md`)
* Convex hull collision schemes (`.sfconvexhullscollisionscheme.sfc`, 31 files)

## Usage

```
python3 dfextract_3.py "<game>/data" export        # unpack dfdata.sfai/.sfad (~14 GB)
python3 sfexport.py all export converted           # models, terrain, collision, animated, maps -> glTF/GLB, PNG, JSON
python3 sfexport.py maps export converted --name k18   # a single piece
python3 -m http.server -d converted 8000           # then open http://localhost:8000/ ... viewer/index.html?file=../maps/k18.glb
```

`sfexport.py` and `sflib.py`/`sfimg.py` use only the Python 3 standard library. Output layout:

| path | content |
| --- | --- |
| `models/*.glb` | static meshes (`.sfm`), textures referenced as `../textures/*.png` |
| `terrain/*.glb` | terrain tiles (`.ter`), preview vertex colours + raw splat weights |
| `collision/<static,dynamic,influence>/*.glb`, `collision/bvh/*.json`, `collision/shapes.json` | collision geometry, BVH, sphere/box shapes |
| `animated/*.glb` | skinned meshes with skeleton (bind pose) |
| `maps/*.json`, `maps/*.glb` | levels: object placements (game coordinates) and an assembled scene |
| `textures/*.png` | DDS/BMP/TGA converted to PNG (max 512px, `--tex-size` to change) |

Coordinates: the game is left handed, Y up. GLBs negate Z (and flip winding) to become glTF's right handed
Y up; the JSON files keep the original game coordinates.

See `FORMATS.md` for what is known about the binary formats.
