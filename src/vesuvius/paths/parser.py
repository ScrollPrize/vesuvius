from lxml import html
import re
import asyncio
import aiohttp
from typing import Dict, Optional, List
from .fetcher import fetch

async def get_directory_structure(url: str, session: aiohttp.ClientSession, ignore_list: Optional[List[str]] = None, zarr_pattern: str = r'\.zarr$') -> Dict[str, Optional[Dict]]:    
    if ignore_list is None:
        ignore_list = []
    
    page_content = await fetch(session, url)
    if not page_content:
        return {}
    
    tree = html.fromstring(page_content)
    directory_tree: Dict[str, Optional[Dict]] = {}
    tasks = []
    hrefs = []

    for element in tree.xpath('//a'):
        href = element.get('href')
        if href and href not in ['../', './'] and '?' not in href:
            full_url = url + href
            if any(re.search(pattern, href) for pattern in ignore_list):
                continue
            if href.endswith('/'):
                tasks.append(get_directory_structure(full_url, session, ignore_list, zarr_pattern))
                hrefs.append(href)
            elif re.search(zarr_pattern, href):
                directory_tree[href] = None
    
    nested_directories = await asyncio.gather(*tasks)
    for idx, href in enumerate(hrefs):
        directory_tree[href] = nested_directories[idx]

    return directory_tree

async def find_zarr_files(tree: Dict[str, Optional[Dict]], url: str, pattern: str, session: aiohttp.ClientSession) -> Dict[str, str]:
    zarr_files: Dict[str, str] = {}
    for key, value in tree.items():
        if isinstance(value, dict):
            nested_zarr = await find_zarr_files(value, url + key, pattern, session)
            if nested_zarr:
                zarr_files[key] = nested_zarr
        elif value is None and re.search(pattern, key):
            zarr_files[key] = url + key
    return zarr_files
