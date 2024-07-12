import os
import yaml
import zarr
import site
import fsspec
from numpy.typing import NDArray
from typing import Any, Dict, Optional, Tuple

class Volume2:
    def __init__(self, type: str, scroll_id: int, energy: int, resolution: float, segment_id: Optional[int] = None, cache: bool = False) -> None:
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
        self.cache = cache

        self.set_filesystem()
        self.data = self.load_data()
    
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
    
    def load_data(self) -> zarr.hierarchy.Group:
        # Map the URL using fsspec with local caching if enabled
        mapper = self.fs.get_mapper(self.url)
        # Open the Zarr file using the mapper
        z = zarr.open(mapper, mode='r')

        return z
    
    def set_filesystem(self) -> None:
        if self.cache:
            self.cache_dir = os.path.join(os.path.expanduser("~"), "vesuvius-data", f"{self.type}s", f"{self.scroll_id}", f"{self.energy}_{self.resolution}")
            if self.segment_id:
                self.cache_dir = os.path.join(self.cache_dir, f"{self.segment_id}")

            os.makedirs(self.cache_dir, exist_ok=True)
            self.fs = fsspec.filesystem("filecache", target_protocol='https', cache_storage=self.cache_dir, same_names=True)
        else:
            self.fs = fsspec.filesystem('https')

    def __getitem__(self, idx: Tuple[int, int, int]) -> NDArray:
        if isinstance(idx, tuple) and len(idx) == 3:
            x, y, z = idx
            return self.data[x, y, z]
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements.")
        
    def activate_caching(self) -> None:
        if not self.cache:
            self.cache = True 
            self.set_filesystem()
            self.data = self.load_data()

    def deactivate_caching(self) -> None:
        if self.cache:
            self.cache = False
            self.set_filesystem()
            self.data = self.load_data()