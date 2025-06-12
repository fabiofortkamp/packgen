# packgen

`packgen` is a tool that generates a packing of particles for various purposes. The primary goal is to generate an STL file with a mesh of the packing.

Currently, only hexagonal particles are implemented. 


## Installation

1. Install [Blender][blender] and add the executable to the Path; it will
be called `Blender` on macOS and `blender` on Linux. I will use `Blender` in the examples
below;
2. Install this project with `pip` or `uv pip`:

```shell
pip install git+https://github.com/cmt-dtu-energy/packgen@v0.2.1
```


## Usage

1. To run it, create a parameter file -- check the [examples](./examples/);
2. Run the following command in a directory where the 
parameter file is located:

```shell
packgen -- <path to the parameter file>
```

You can name the parameters file in any way you want; this command will open Blender,
simulate the packing, and then save `.blender` and `.stl` files in the current
directory. The filenames will have file names as `packing_<basename of parameter file>.<extention>`.

If you omit the `-- <path to the parameter file>` part, by default `packgen` will read
a file named `parameters.json` in the current directory.


[blender]: https://www.blender.org/
