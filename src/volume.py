import os
import yaml
import zarr
import site
import fsspec
from typing import Any, Dict

class Scroll:
    def __init__(self, id: int, energy: int, resolution: float) -> None:
        self.id = id
        self.scrolls_path = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', 'scrolls.yaml')
        self.energy = energy
        self.resolution = resolution
        self.url = self.get_url_from_yaml(id, energy, resolution)
        self.cache_dir = os.path.join(os.path.expanduser("~"), "vesuvius-data", "scrolls", f"{id}", f"{energy}_{resolution}")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.fs = fsspec.filesystem("filecache", target_protocol='https', cache_storage=self.cache_dir)
        self.data = self.load_data()
    
    def get_url_from_yaml(self, id: str, energy: int, resolution: float) -> str:
        # Load the YAML file
        with open(self.scrolls_path, 'r') as file:
            data: Dict[str, Any] = yaml.safe_load(file)
        
        # Retrieve the URL for the given id, energy, and resolution
        url: str = data.get(id, {}).get(energy, {}).get(resolution)
        if url is None:
            raise ValueError(f"URL not found for scroll: {id}, energy: {energy}, resolution: {resolution}")
        
        return url
    
    def load_data(self) -> zarr.hierarchy.Group:
        # Map the URL using fsspec with local caching
        mapper = self.fs.get_mapper(self.url)
        # Open the Zarr file using the mapper
        z = zarr.open(mapper, mode='r')
        return z