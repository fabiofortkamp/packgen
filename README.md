# packgen

`packgen` is a tool that generates a packing of particles for various purposes. The primary goal is to generate an STL file with a mesh of the packing.

Currently, only hexagonal particles are implemented. 

## Usage

1. Install [Blender][blender] and add the executable to the Path; it will
be called `Blender` on macOS and `blender` on Linux. I will use `Blender` in the examples
below;
2. To run it, create a parameter file similar to the [example one](./parameters.json).
3. Run the following command in a directory where the 
parameter file is located:

```shell
Blender -P <path to the src/packgen/blend.py script> -- parameters.json
```

You can name the parameters file in any way you want; this command will open Blender,
simulate the packing, and then save `.blender` and `.stl` files in the current
directory. The filenames will have file names as `packing_<basename of parameter file>.<extention>`.

[blender]: https://www.blender.org/
