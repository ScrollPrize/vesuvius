# vesuvius
A Python library for accessing Vesuvius Challenge data.

## Installation
To install the Vesuvius library, run:
```sh
pip install . -v
```

## Usage
Before using the library, ensure you accept the terms:
```python
vesuvius.accept_terms()
```

### Importing Volume
To import and use the `Volume` class:
```python
from vesuvius import Volume

# Basic usage
scroll = Volume("scroll", 1, 54, 7.91)

# With cache (works only with remote repository)
scroll = Volume("scroll", 1, 54, 7.91, cache=True)

# Deactivate/activate caching (works only with remote repository)
scroll.activate_caching()
scroll.deactivate_caching()

# With normalization
scroll = Volume("scroll", 1, 54, 7.91, normalize=True)

# With local files
scroll = Volume("scroll", 1, 54, 7.91, domain="local", path="/home/giorgio/Downloads/54keV_7.91mum.zarr")

# To access shapes of multiresolution arrays
subvolume_index = 3 # third subvolume
scroll.shape(subvolume_index)

# To access dtype
scroll.dtype
```
### Importing Cube
To import and use the `Cube` class:
```python
from vesuvius import Cube

# Basic usage
cube = Cube("scroll", 1, 54, 7.91, z=2256,y=2512,x=4816, cache=True, cache_dir='/home/giorgio/Projects/vesuvius/dev_jupyter/cache') # with caching

cube = Cube("scroll", 1, 54, 7.91, z=2256,y=2512,x=4816) # without caching

# as before normalize=True will provide a normalized volume (not masks)

# Deactivate/activate caching (works only with remote repository)
cube.activate_caching() # make sure that a proper cache_dir is defined
cube.deactivate_caching()

# To access the volume and the masks
volume, mask = cube[:,:,:] # also works with slicing

### Listing Files
To list available files in the remote repository:
```python
from vesuvius import list

files = vesuvius.list()
```
