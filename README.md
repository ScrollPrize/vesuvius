# vesuvius
From [Vesuvius Challenge](https://scrollprize.org), a Python library for accessing CT scans of ancient scrolls.

`vesuvius` allows direct access to scroll data **without** managing download scripts or storing terabytes of CT scans locally:

```python
import vesuvius

scroll1 = vesuvius.Volume("Scroll1")
img = scroll[3,1000,:,:]

plt.imshow(img)
```

<img src="img/slice.png" alt="drawing" width="200"/>

Data is streamed in the background, only serving the requested portions.

The library provides tools for accessing, managing, and manipulating high-resolution volumetric and segmented data related to the Vesuvius Challenge. It supports both remote data retrieval and local file handling, with options for data caching and normalization.

### What It Does
- **Data Retrieval**: Fetches volumetric scroll data, surface volume of segmented areas and annotated volumetric cubes from remote repositories or local files.
- **Data Listing**: Traverses the remote repository and automatically update a list of available data.
- **Data Caching**: Supports caching of data to improve performance when accessing remote repositories.
- **Normalization**: Provides options to normalize data values.
- **Multiresolution Handling**: Manages and accesses data at multiple resolutions.

### What It Doesn't Do
- **Remote Data Modification**: The library does not support modifying the original data.
- **Complex Analysis**: While it provides access to data, it does not include built-in tools for complex data analysis or visualization.
- **Unsupported Data Types**: Only supports specific data types (volumetric and segmented data in specific formats like Zarr and NRRD). Other data formats are not supported.

## Installation
```sh
$ pip install vesuvius
```

## Usage
Before using the library for the first time, accept the license terms:
```sh
$ vesuvius.accept_terms --yes
```

After this the library can be imported in Python:
```python
import vesuvius
```

### Listing

#### Listing files
To list the available files in the remote repository, use the following code:

```python
from vesuvius import list_files

files = list_files()
```

The output of `list_files` is a dictionary that contains the paths to all the scroll volumes and segment surface volumes available in the data repository. The dictionary structure is as follows:

- The top-level keys are `scroll_id`.
- Under each `scroll_id`, there are keys for different `energy` levels.
- Under each `energy`, there are keys for different `resolution` levels.
- Under each `resolution`, there are keys for either `segments` or `volume`.

`segments` can contain `segment_id`s.

Here is a visual representation of what the dictionary can look like:

```plaintext
{
  'scroll_id1': {
    'energy1': {
      'resolution1': {
        'segments': {
          'segment_id1': 'path/to/segment_id1',
          'segment_id2': 'path/to/segment_id2'
        },
        'volume': 'path/to/volumes'
      },
      'resolution2': {
        'segments': {
          'segment_id1': 'path/to/segment_id1',
          'segment_id2': 'path/to/segment_id2'
        },
        'volume': 'path/to/volumes'
      }
    },
    'energy2': {
      'resolution1': {
        'segments': {
          'segment_id1': 'path/to/segment_id1',
          'segment_id2': 'path/to/segment_id2'
        },
        'volume': 'path/to/volume'
      },
    }
  },
  'scroll_id2': {
    'energy1': {
      'resolution1': {
        'segments': {
          'segment_id1': 'path/to/segment_id1',
          'segment_id2': 'path/to/segment_id2'
        },
        'volume': 'path/to/volumes'
      },
    }
  }
}
```

This structure allows you to access specific paths based on the `scroll_id`, `energy`, `resolution`, and `segment_id` of the data you are interested in. This function is automatically executed when the library is imported to constantly keep the list of available files updated.

#### Listing cubes
To list the available instance annotated volumetric cubes:
```python
from vesuvius import cubes

available_cubes = cubes()
```

Similarly to `list_files` the output of `cubes` is a dictionary:
```plaintext
{
  'scroll_id1': {
    'energy1': {
      'resolution1': {
        'z1_y1_x1': 'path/to/z1_y1_x1',
        'z2_y2_x2': 'path/to/z2_y2_x2'
        }
      }
    }
}
```
`z_y_x` are the coordinates in the relative scroll volume of the origin of the reference frame of the selected cube.

### Importing and Using `Volume`
The `Volume` class is used for accessing volumetric data, both for scrolls and surface volume of segments.

#### Example Usage
```python
from vesuvius import Volume
# Basic usage
scroll = Volume(type="scroll1") # this is going to access directly the canonical scroll 1 volume

# Basic usage specifying scan metadata
scroll = Volume(type="scroll", scroll_id=1, energy=54, resolution=7.91) # if you want to access a non canonical volume, you have to specify the scan metadata

# With cache (works only with remote repository)
scroll = Volume(type="scroll", scroll_id=1, energy=54, resolution=7.91, cache=True)

# Deactivate/activate caching (works only with remote repository)
scroll.activate_caching()
scroll.deactivate_caching()

# With normalization
scroll = Volume(type="scroll", scroll_id=1, energy=54, resolution=7.91, normalize=True)

# With local files
scroll = Volume(type="scroll", scroll_id=1, energy=54, resolution=7.91, domain="local", path="/path/to/54keV_7.91um.zarr")

# To access shapes of multiresolution arrays
subvolume_index = 3  # third subvolume
shape = scroll.shape(subvolume_index)

# To access dtype
dtype = scroll.dtype

# Access data using indexing
data = scroll[0, :, :, :]  # Access the entire first subvolume
```

You can access segments in a similar fashion:
```python
from vesuvius import Volume
# Basic usage
segment = Volume("20230827161847") # access a segment specifying is unique timestamp

# Basic usage specifying scan metadata
segment = Volume(type="segment", scroll_id=1, energy=54, resolution=7.91, segment_id=20230827161847)

```
#### Constructor
```python
Volume(
    type: Union[str, int],
    scroll_id: Optional[int] = None,
    energy: Optional[int] = None,
    resolution: Optional[float] = None,
    segment_id: Optional[int] = None,
    cache: bool = False,
    cache_pool: int = 1e10,
    normalize: bool = False,
    verbose: bool = True,
    domain: str = "dl.ash2txt",
    path: Optional[str] = None
)
```
- **type**: Type of volume, either 'scroll', 'scroll#' or 'segment'.
- **scroll_id**: Identifier for the scroll.
- **energy**: Energy level.
- **resolution**: Resolution level.
- **segment_id**: Identifier for the segment.
- **cache**: Enable caching.
- **cache_pool**: Cache pool size.
- **normalize**: Normalize the data.
- **verbose**: Enable verbose output.
- **domain**: Domain, either 'dl.ash2txt' or 'local'.
- **path**: Path to the local data.

#### Methods
- **activate_caching()**: Activates caching.
- **deactivate_caching()**: Deactivates caching.
- **shape(subvolume_idx: int = 0)**: Returns the shape of the specified subvolume.

### Importing and Using `Cube`
The `Cube` class is used for accessing segmented cube data.

#### Example Usage
```python
from vesuvius import Cube

# Basic usage
cube = Cube(scroll_id=1, energy=54, resolution=7.91, z=2256, y=2512, x=4816, cache=True, cache_dir='/path/to/cache')  # with caching

cube = Cube(scroll_id=1, energy=54, resolution=7.91, z=2256, y=2512, x=4816)  # without caching

# With normalization
cube = Cube(scroll_id=1, energy=54, resolution=7.91, z=2256, y=2512, x=4816, normalize=True)

# Deactivate/activate caching (works only with remote repository)
cube.activate_caching()  # make sure that a proper cache_dir is defined
cube.deactivate_caching()

# To access the volume and the masks
volume, mask = cube[:, :, :]  # also works with slicing
```

#### Constructor
```python
Cube(
    scroll_id: int,
    energy: int,
    resolution: float,
    z: int,
    y: int,
    x: int,
    cache: bool = False,
    cache_dir: Optional[os.PathLike] = None,
    normalize: bool = False
)
```
- **scroll_id**: Identifier for the scroll.
- **energy**: Energy level.
- **resolution**: Resolution level.
- **z**: Z-coordinate.
- **y**: Y-coordinate.
- **x**: X-coordinate.
- **cache**: Enable caching.
- **cache_dir**: Directory for cache.
- **normalize**: Normalize the data.

#### Methods
- **load_data()**: Loads data.
- **activate_caching()**: Activates caching.
- **deactivate_caching()**: Deactivates caching.

## Additional Notes
- **Terms Acceptance**: Ensure that the terms are accepted before using the library.
- **Caching**: Caching is only supported with the remote repository.
- **Normalization**: The `normalize` parameter normalizes the data to the maximum value of the dtype.
- **Local Files**: For local files, provide the appropriate path in the `Volume` constructor.

## Introductory notebooks
For an example of how to use the `Volume` class, please play with this [Colab notebook](https://gist.github.com/giorgioangel/40ec66262b42b96c3176dd43f55d23f1#file-scroll-data-access-ipynb).

This [other Colab notebook](https://colab.research.google.com/gist/giorgioangel/3862d226ff87dacd368608f7ad3d55b9/cubes-bootstrap.ipynb) shows how to access to the instance annotated cubes.