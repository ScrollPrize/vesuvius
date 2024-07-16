import asyncio
import aiohttp
import yaml
from typing import List, Optional, Dict, Tuple
from .parser import get_directory_structure, find_zarr_files
import nest_asyncio
import ssl

async def scrape_website(base_url: str, ignore_list: List[str], zarr_pattern: str) -> Tuple[Dict[str, Optional[Dict]], Dict[str, str]]:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=aiohttp.ClientTimeout(total=60)) as session:
        directory_tree = await get_directory_structure(base_url, session, ignore_list)
        zarr_files = await find_zarr_files(directory_tree, base_url, zarr_pattern, session)
        return directory_tree, zarr_files

def list_files(base_url: str, ignore_list: Optional[List[str]] = None, zarr_pattern: str = r'\.zarr$') -> None:
    if ignore_list is None:
        ignore_list = [r'\.zarr$', r'some_other_pattern']
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        nest_asyncio.apply()
        tree, zarr_files = loop.run_until_complete(scrape_website(base_url, ignore_list, zarr_pattern))
    else:
        tree, zarr_files = loop.run_until_complete(scrape_website(base_url, ignore_list, zarr_pattern))
    
    with open('directory_structure.yaml', 'w') as file:
        yaml.dump(tree, file, default_flow_style=False)
    
    with open('zarr_files.yaml', 'w') as file:
        yaml.dump(zarr_files, file, default_flow_style=False)
    
    print("Directory structure saved to 'directory_structure.yaml'")
    print(".zarr files saved to 'zarr_files.yaml'")
