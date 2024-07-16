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

### Listing Files
To list available files in the remote repository:
```python
from vesuvius import list

files = vesuvius.list()
```