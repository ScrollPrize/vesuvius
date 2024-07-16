import os
import yaml
import site
import tensorstore as ts
from numpy.typing import NDArray
from typing import Any, Dict, Optional, Tuple, Union, List
import numpy as np
import requests

# Function to get the maximum value of a dtype
def get_max_value(dtype: np.dtype) -> Union[float, int]:
    if np.issubdtype(dtype, np.floating):
        max_value = np.finfo(dtype).max
    elif np.issubdtype(dtype, np.integer):
        max_value = np.iinfo(dtype).max
    else:
        raise ValueError("Unsupported dtype")
    return max_value
    
class Volume:
    def __init__(self, type: str, scroll_id: int, energy: int, resolution: float, segment_id: Optional[int] = None, cache: bool = False, normalize: bool = False, verbose : bool = True) -> None:
        assert type in ["scroll", "segment"], "type should be either 'scroll' or 'segment'"
        self.type = type

        if type == "segment":
            assert isinstance(segment_id, int), "segment_id must be an int when type is 'segment'"
            self.segment_id = segment_id
        else:
            self.segment_id = None

        self.scroll_id = scroll_id
        self.configs = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'{type}s.yaml')
        self.energy = energy
        self.resolution = resolution
        self.url = self.get_url_from_yaml()
        self.metadata = self.load_ome_metadata()
        self.cache = cache
        self.normalize = normalize
        self.verbose = verbose

        self.data = self.load_data()

        if self.verbose:
            # Assuming the first dataset is the original resolution
            original_dataset = self.metadata['zattrs']['multiscales'][0]['datasets'][0]
            original_scale = original_dataset['coordinateTransformations'][0]['scale'][0]
            original_resolution = self.resolution * original_scale
            idx = 0
            print(f"Data with original resolution: {original_resolution} mum, subvolume idx: {idx}, shape: {self.shape(idx)}")

            # Loop through the datasets to print the scaled resolutions, excluding the first one
            for dataset in self.metadata['zattrs']['multiscales'][0]['datasets'][1:]:
                idx += 1
                scale_factors = dataset['coordinateTransformations'][0]['scale']
                scaled_resolution = self.resolution * scale_factors[0]
                print(f"Contains also data with scaled resolution: {scaled_resolution} mum, subvolume idx: {idx}, shape: {self.shape(idx)}")

        if self.normalize:
            self.max_dtype = get_max_value(self.data[0].dtype.numpy_dtype)

        self.dtype = self.data[0].dtype.numpy_dtype
        
    def get_url_from_yaml(self) -> str:
        # Load the YAML file
        with open(self.configs, 'r') as file:
            data: Dict[str, Any] = yaml.safe_load(file)
        
        # Retrieve the URL for the given id, energy, and resolution
        if self.type == 'scroll':
            url: str = data.get(self.scroll_id, {}).get(self.energy, {}).get(self.resolution)
        elif self.type == 'segment':
            url: str = data.get(self.scroll_id, {}).get(self.energy, {}).get(self.resolution, {}).get(self.segment_id)

        if url is None:
            if self.type == 'scroll':
                raise ValueError(f"URL not found for scroll: {self.scroll_id}, energy: {self.energy}, resolution: {self.resolution}")
            elif self.type == 'segment':
                raise ValueError(f"URL not found for scroll: {self.scroll_id}, energy: {self.energy}, resolution: {self.resolution}, segment: {self.segment_id}")
            else:
                raise ValueError("URL not found.")
            
        return url
    
    def load_ome_metadata(self) -> None:
        try:
            # Load the .zattrs metadata
            zattrs_url = f"{self.url}/.zattrs"
            zattrs_response = requests.get(zattrs_url)
            zattrs_response.raise_for_status()
            zattrs = zattrs_response.json()

            # Load the .zgroup metadata
            zgroup_url = f"{self.url}/.zgroup"
            zgroup_response = requests.get(zgroup_url)
            zgroup_response.raise_for_status()
            zgroup = zgroup_response.json()
            
            return {
                "zattrs": zattrs,
                "zgroup": zgroup
            }
        except requests.RequestException as e:
            print(f"Error loading metadata: {e}")
            raise

    def load_data(self) -> List[ts.TensorStore]:
        if self.cache:
            context_spec = {
                'cache_pool': {
                    "total_bytes_limit": 10000000 #TODO: set this... or manage better local cache!
                }
            }
        else:
            context_spec = {}

        sub_volumes = []
        for dataset in self.metadata['zattrs']['multiscales'][0]['datasets']:
            path = dataset['path']
            sub_url = f"{self.url}/{path}/"
            kvstore_spec = {
                'driver': 'http',
                'base_url': sub_url
            }
            
            spec = {
                'driver': 'zarr',
                'kvstore': kvstore_spec,
                'context': context_spec
            }

            # Print the full URL for debugging
            #print(f"Attempting to load data from: {sub_url}.zarray")
            
            try:
                data = ts.open(spec).result()
                sub_volumes.append(data)
            except Exception as e:
                print(f"Error loading data from {sub_url}: {e}")
                raise

        return sub_volumes

    '''
    def get_cache_dir(self) -> str:
        cache_dir = os.path.join(os.path.expanduser("~"), "vesuvius-data", f"{self.type}s", f"{self.scroll_id}", f"{self.energy}_{self.resolution}")
        if self.segment_id:
            cache_dir = os.path.join(cache_dir, f"{self.segment_id}")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir'''
    
    def __getitem__(self, idx: Tuple[int, ...]) -> NDArray:

        if isinstance(idx, tuple) and len(idx) == 4:
            subvolume_idx, x, y, z = idx

            assert 0 <= subvolume_idx < len(self.data), "Invalid subvolume index."
            if self.normalize:
                return self.data[subvolume_idx][x, y, z].read().result()/self.max_dtype
            
            else:
                return self.data[subvolume_idx][x,y,z].read().result()
            
        elif isinstance(idx, tuple) and len(idx) == 3:
            x, y, z = idx

            subvolume_idx = 0

            if self.normalize:
                return self.data[subvolume_idx][x, y, z].read().result()/self.max_dtype
            
            else:
                return self.data[subvolume_idx][x,y,z].read().result()
        
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements (coordinates) or four elements (subvolume id and coordinates).")
    
    def activate_caching(self) -> None:
        if not self.cache:
            self.cache = True
            self.data = self.load_data()

    def deactivate_caching(self) -> None:
        if self.cache:
            self.cache = False
            self.data = self.load_data()

    def shape(self, subvolume_idx: int = 0) -> Tuple[int, ...]:
        assert 0 <= subvolume_idx < len(self.data), "Invalid subvolume index"
        return self.data[subvolume_idx].shape
    
# TODO: Doesnt work yet
class Cube:
    def __init__(self, scroll_id: int, energy: int, resolution: float, z: int, y: int, x: int, cache: bool = False, normalize: bool = False) -> None:
        self.scroll_id = scroll_id
        self.configs = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'cubes.yaml')
        self.energy = energy
        self.resolution = resolution
        self.z, self.y, self.x = z, y, x
        self.volume_url, self.mask_url = self.get_url_from_yaml()
        self.cache = cache
        self.normalize = normalize

        self.volume, self.mask = self.load_data()

        if self.normalize:
            self.max_dtype = get_max_value(self.volume.dtype.numpy_dtype)
        
    def get_url_from_yaml(self) -> str:
        # Load the YAML file
        with open(self.configs, 'r') as file:
            data: Dict[str, Any] = yaml.safe_load(file)
        
        # Retrieve the URL for the given id, energy, and resolution
        base_url: str = data.get(self.scroll_id, {}).get(self.energy, {}).get(self.resolution, {}).get(f"{self.z:05d}_{self.y:05d}_{self.x:05d}")
        print(base_url)
        if base_url is None:
                raise ValueError("URL not found.")

        volume_url = base_url + f"{self.z:05d}_{self.y:05d}_{self.x:05d}_volume.nrrd"
        mask_url = base_url + f"{self.z:05d}_{self.y:05d}_{self.x:05d}_mask.nrrd"
        print(volume_url)
        return volume_url, mask_url
    
    def load_data(self) -> Tuple[ts.TensorStore, ts.TensorStore]:
        if self.cache:
            context_spec = {
                'cache_pool': {
                    "total_bytes_limit": 10000000 #TODO: set this... or manage better local cache!
                }
            }
        else:
            context_spec = {}

        kvstore_spec_volume = {
            'driver': 'http',
            'base_url': self.volume_url,
        }

        kvstore_spec_mask = {
            'driver': 'http',
            'base_url': self.mask_url,
        }

        spec_volume = {
            'driver': 'nrrd',
            'kvstore': kvstore_spec_volume,
            'context': context_spec,
        }

        spec_mask = {
            'driver': 'nrrd',
            'kvstore': kvstore_spec_mask,
            'context': context_spec,
        }

        return ts.open(spec_volume).result(), ts.open(spec_mask).result()

    '''
    def get_cache_dir(self) -> str:
        cache_dir = os.path.join(os.path.expanduser("~"), "vesuvius-data", f"{self.type}s", f"{self.scroll_id}", f"{self.energy}_{self.resolution}")
        if self.segment_id:
            cache_dir = os.path.join(cache_dir, f"{self.segment_id}")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir'''
    
    def __getitem__(self, idx: Tuple[int, ...]) -> NDArray:
        if isinstance(idx, tuple) and len(idx) == 3:
            zz, yy, xx = idx

            if self.normalize:
                return self.volume[zz, yy, xx].read().result()/self.max_dtype, self.mask[zz, yy, xx].read().result()
            
            else:
                return self.volume[zz, yy, xx].read().result(), self.mask[zz, yy, xx].read().result()
            
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements.")
    
    def activate_caching(self) -> None:
        if not self.cache:
            self.cache = True
            self.volume, self.mask = self.load_data()

    def deactivate_caching(self) -> None:
        if self.cache:
            self.cache = False
            self.volume, self.mask = self.load_data()

