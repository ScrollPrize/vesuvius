import os
import yaml
import site
import tensorstore as ts
from numpy.typing import NDArray
from typing import Any, Dict, Optional, Tuple

class Volume:
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
    
    def load_data(self) -> ts.TensorStore:
        if self.cache:
            context_spec = {
                'cache_pool': {
                    "total_bytes_limit": 10000000 #TODO: set this... or manage better local cache!
                }
            }
        else:
            context_spec = {}

        kvstore_spec = {
            'driver': 'http',
            'base_url': self.url,
        }

        spec = {
            'driver': 'zarr',
            'kvstore': kvstore_spec,
            'context': context_spec,
        }

        return ts.open(spec).result()

    '''
    def get_cache_dir(self) -> str:
        cache_dir = os.path.join(os.path.expanduser("~"), "vesuvius-data", f"{self.type}s", f"{self.scroll_id}", f"{self.energy}_{self.resolution}")
        if self.segment_id:
            cache_dir = os.path.join(cache_dir, f"{self.segment_id}")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir'''
    
    def __getitem__(self, idx: Tuple[int, int, int]) -> NDArray:
        if isinstance(idx, tuple) and len(idx) == 3:
            x, y, z = idx
            return self.data[x, y, z].read().result()
        else:
            raise IndexError("Invalid index. Must be a tuple of three elements.")
    
    def activate_caching(self) -> None:
        if not self.cache:
            self.cache = True
            self.data = self.load_data()

    def deactivate_caching(self) -> None:
        if self.cache:
            self.cache = False
            self.data = self.load_data()
