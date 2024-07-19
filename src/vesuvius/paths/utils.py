import asyncio
import aiohttp
import yaml
from typing import List, Optional, Dict, Tuple
from .parser import get_directory_structure, find_zarr_files, list_subfolders
import nest_asyncio
import ssl
import site
import os

async def scrape_website(base_url: str, ignore_list: List[str]) -> Tuple[Dict[str, Optional[Dict]], Dict[str, str]]:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=aiohttp.ClientTimeout(total=60)) as session:
        directory_tree = await get_directory_structure(base_url, session, ignore_list)
        zarr_files = await find_zarr_files(directory_tree, base_url, session)
        return directory_tree, zarr_files

# Define the function to scrape the website and generate the YAML
async def collect_subfolders(base_url: str, ignore_list: List[str]) -> List[str]:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=aiohttp.ClientTimeout(total=60)) as session:
        subfolders = await list_subfolders(base_url, session, ignore_list)
        return subfolders
    
def update_list(base_url: str, base_url_cubes: str, ignore_list: Optional[List[str]] = None) -> None:
    scroll_config = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'scrolls.yaml')
    directory_config = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'directory_structure.yaml')
    cubes_config = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'cubes.yaml')

    if ignore_list is None:
        ignore_list = [r'\.zarr$', r'some_other_pattern']
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        nest_asyncio.apply()
        tree, zarr_files = loop.run_until_complete(scrape_website(base_url, ignore_list))
        cubes_folders = loop.run_until_complete(scrape_website(base_url_cubes, ignore_list))
    else:
        tree, zarr_files = loop.run_until_complete(scrape_website(base_url, ignore_list))
        cubes_folders = loop.run_until_complete(scrape_website(base_url_cubes, ignore_list))

    with open(directory_config, 'w') as file:
        yaml.dump(tree, file, default_flow_style=False)
    
    with open(scroll_config, 'w') as file:
        yaml.dump(zarr_files, file, default_flow_style=False)


    #TODO: implement not only for scroll 1
    #TODO: fix cubes path on website
    data = {
            1: {
                54: {
                    7.91: { }
                }
            }}
    for folder in cubes_folders[0].keys():
        # Extract the name of the first subfolder
        folder_name = folder[:-1]
        data[1][54][7.91][folder_name] = base_url_cubes + folder

    with open(cubes_config, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)
    
    #print("Directory structure saved to 'directory_structure.yaml'")
    #print("Scrolls paths saved to 'scrolls.yaml'")

def list_files() -> Dict:
    scroll_config = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'scrolls.yaml')
    with open(scroll_config, 'r') as file:
        data = yaml.safe_load(file)
    return data

def list_cubes() -> Dict:
    cubes_config = os.path.join(site.getsitepackages()[-1], 'vesuvius', 'configs', f'cubes.yaml')
    with open(cubes_config, 'r') as file:
        data = yaml.safe_load(file)
    return data
