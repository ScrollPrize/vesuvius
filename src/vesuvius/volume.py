import os
import yaml
import site
import tensorstore as ts
from numpy.typing import NDArray
from typing import Any, Dict, Optional, Tuple, Union, List
import numpy as np
import requests
import zarr
import nrrd
import tempfile

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
    def __init__(self, type: str, scroll_id: int, energy: int, resolution: float, segment_id: Optional[int] = None, cache: bool = False, normalize: bool = False, verbose : bool = True, domain: str = "dl.ash2txt", path: Optional[str] = None) -> None:
        assert type in ["scroll", "segment"], "type should be either 'scroll' or 'segment'"
        self.type = type

        if type == "segment":
            assert isinstance(segment_id, int), "segment_id must be an int when type is 'segment'"
            self.segment_id = segment_id
        else:
            self.segment_id = None

        assert domain in ["dl.ash2txt", "local"], "domain should be dl.ash2txt or local"

        if domain == "local":
            assert path is not None

        self.scroll_id = scroll_id
        self.configs = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'scrolls.yaml')
        self.energy = energy
        self.resolution = resolution
        self.domain = domain
        self.cache = cache
        self.normalize = normalize
        self.verbose = verbose

        if self.domain == "dl.ash2txt":
            self.url = self.get_url_from_yaml()
            self.metadata = self.load_ome_metadata()
            self.data = self.load_data()
            if self.normalize:
                self.max_dtype = get_max_value(self.data[0].dtype.numpy_dtype)
            self.dtype = self.data[0].dtype.numpy_dtype
        elif self.domain == "local":
            self.url = path
            self.data = zarr.open(self.url, mode="r")
            self.metadata = self.load_ome_metadata()
            if self.normalize:
                self.max_dtype = get_max_value(self.data[0].dtype)
            self.dtype = self.data[0].dtype

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

        
    def get_url_from_yaml(self) -> str:
        # Load the YAML file
        with open(self.configs, 'r') as file:
            data: Dict[str, Any] = yaml.safe_load(file)
        
        # Retrieve the URL for the given id, energy, and resolution
        if self.type == 'scroll':
            url: str = data.get(str(self.scroll_id), {}).get(str(self.energy), {}).get(str(self.resolution), {}).get("volume")
        elif self.type == 'segment':
            url: str = data.get(str(self.scroll_id), {}).get(str(self.energy), {}).get(str(self.resolution), {}).get("segments", {}).get(str(self.segment_id))

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
            if self.domain == "dl.ash2txt":
                # Load the .zattrs metadata
                zattrs_url = f"{self.url}/.zattrs"
                zattrs_response = requests.get(zattrs_url)
                zattrs_response.raise_for_status()
                zattrs = zattrs_response.json()

            elif self.domain == "local":
                zattrs = dict(self.data.attrs)
            return {
                "zattrs": zattrs,
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
            if self.domain == "dl.ash2txt":
                if self.normalize:
                    return self.data[subvolume_idx][x, y, z].read().result()/self.max_dtype
                else:
                    return self.data[subvolume_idx][x,y,z].read().result()
                
            elif self.domain == "local":
                if self.normalize:
                    return self.data[subvolume_idx][x, y, z]/self.max_dtype
                else:
                    return self.data[subvolume_idx][x,y,z]
            else:
                raise ValueError("Invalid domain.")
            
        elif isinstance(idx, tuple) and len(idx) == 3:
            x, y, z = idx

            subvolume_idx = 0

            if self.domain == "dl.ash2txt":
                if self.normalize:
                    return self.data[subvolume_idx][x, y, z].read().result()/self.max_dtype
                
                else:
                    return self.data[subvolume_idx][x,y,z].read().result()
                
            elif self.domain == "local":
                if self.normalize:
                    return self.data[subvolume_idx][x, y, z]/self.max_dtype
                
                else:
                    return self.data[subvolume_idx][x,y,z]
            else:
                raise ValueError("Invalid domain.")
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements (coordinates) or four elements (subvolume id and coordinates).")
    
    def activate_caching(self) -> None:
        if self.domain != "local":
            if not self.cache:
                self.cache = True
                self.data = self.load_data()

    def deactivate_caching(self) -> None:
        if self.domain != "local":
            if self.cache:
                self.cache = False
                self.data = self.load_data()

    def shape(self, subvolume_idx: int = 0) -> Tuple[int, ...]:
        assert 0 <= subvolume_idx < len(self.data), "Invalid subvolume index"
        return self.data[subvolume_idx].shape
    
#TODO: fix cubes path on website
class Cube:
    def __init__(self, scroll_id: int, energy: int, resolution: float, z: int, y: int, x: int, cache: bool = False, cache_dir : Optional[os.PathLike] = None, normalize: bool = False) -> None:
        self.scroll_id = scroll_id
        self.configs = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'cubes.yaml')
        self.energy = energy
        self.resolution = resolution
        self.z, self.y, self.x = z, y, x
        self.volume_url, self.mask_url = self.get_url_from_yaml()
        self.cache = cache
        if self.cache:
            self.cache_dir = cache_dir
            os.makedirs(self.cache_dir, exist_ok=True)
        self.normalize = normalize

        self.volume, self.mask = self.load_data()

        if self.normalize:
            self.max_dtype = get_max_value(self.volume.dtype)
        
    def get_url_from_yaml(self) -> str:
        # Load the YAML file
        with open(self.configs, 'r') as file:
            data: Dict[str, Any] = yaml.safe_load(file)
        
        # Retrieve the URL for the given id, energy, and resolution
        base_url: str = data.get(self.scroll_id, {}).get(self.energy, {}).get(self.resolution, {}).get(f"{self.z:05d}_{self.y:05d}_{self.x:05d}")
        if base_url is None:
                raise ValueError("URL not found.")

        volume_url = base_url + f"{self.z:05d}_{self.y:05d}_{self.x:05d}_volume.nrrd"
        mask_url = base_url + f"{self.z:05d}_{self.y:05d}_{self.x:05d}_mask.nrrd"
        return volume_url, mask_url
    
    def load_data(self) -> Tuple[NDArray, NDArray]:
        output = []
        for url in [self.volume_url, self.mask_url]:
            if self.cache:
                # Extract the relevant path after "finished_cubes"
                path_after_finished_cubes = url.split('finished_cubes/')[1]
                # Extract the directory structure and the filename
                dir_structure, filename = os.path.split(path_after_finished_cubes)

                # Create the full directory path in the temp_dir
                full_temp_dir_path = os.path.join(self.cache_dir, dir_structure)

                # Make sure the directory structure exists
                os.makedirs(full_temp_dir_path, exist_ok=True)

                # Create the full path for the temporary file
                temp_file_path = os.path.join(full_temp_dir_path, filename)

                # Check if the file already exists in the cache
                if os.path.exists(temp_file_path):
                    # Read the NRRD file from the cache
                    array, _ = nrrd.read(temp_file_path)

                else:
                    # Download the remote file
                    response = requests.get(url)
                    response.raise_for_status()  # Ensure we notice bad responses
                    # Write the downloaded content to the temporary file with the same directory structure and filename
                    with open(temp_file_path, 'wb') as tmp_file:
                        tmp_file.write(response.content)

                        array, _ = nrrd.read(temp_file_path)

            else:
                response = requests.get(url)
                response.raise_for_status()  # Ensure we notice bad responses
                with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                    tmp_file.write(response.content)
                    temp_file_path = tmp_file.name
                    # Read the NRRD file from the temporary file

                    array, _ = nrrd.read(temp_file_path)

            output.append(array)

        return output[0], output[1]


    def __getitem__(self, idx: Tuple[int, ...]) -> NDArray:
        if isinstance(idx, tuple) and len(idx) == 3:
            zz, yy, xx = idx

            if self.normalize:
                return self.volume[zz, yy, xx]/self.max_dtype, self.mask[zz, yy, xx]
            
            else:
                return self.volume[zz, yy, xx], self.mask[zz, yy, xx]
            
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements.")
    
    def activate_caching(self) -> None:
        if not self.cache:
            assert self.cache_dir is not None, "attribute cache_dir is None, define it first!"
            self.cache = True
            self.volume, self.mask = self.load_data()

    def deactivate_caching(self) -> None:
        if self.cache:
            self.cache = False
            self.volume, self.mask = self.load_data()

