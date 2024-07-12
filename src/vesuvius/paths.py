import requests
import yaml
import os
import re
from tqdm import tqdm

# TODO: more efficient, async, multi-thread, restricted path structure

# Function to fetch content from a URL
def fetch_content(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

# Function to check if a URL is a directory
def is_directory(url):
    return url.endswith('/')

# Function to get subdirectories from a URL
def get_subdirectories(url):
    content = fetch_content(url)
    # Extract href links directly using regex
    links = re.findall(r'href="([^"]+)"', content)
    # Filter out links that are not directories or that navigate back to the parent directory
    directories = [link for link in links if is_directory(link) and link != '../']
    return directories

# Function to traverse directory paths and collect information
def traverse_directory(url, base_url, result_list, current_path=[]):
    directories = get_subdirectories(url)
    for directory in tqdm(directories, desc=f"Traversing {url}"):
        full_url = os.path.join(url, directory)
        relative_path = os.path.join(*current_path, directory.rstrip('/'))
        result_list.append(relative_path)
        traverse_directory(full_url, base_url, result_list, current_path + [directory.rstrip('/')])

# Function to save results to a YAML file
def save_to_yaml(file_path, data):
    with open(file_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)

# Main function to start the traversal
def main(base_url, yaml_output_path):
    result_list = []
    traverse_directory(base_url, base_url, result_list)
    
    # Create a structured data format for YAML
    structured_data = {
        'directories': result_list
    }
    
    save_to_yaml(yaml_output_path, structured_data)
    print(f"YAML file saved to {yaml_output_path}")

# Example usage
if __name__ == '__main__':
    base_url = 'https://registeredusers:only@dl.ash2txt.org/full-scrolls/'
    yaml_output_path = 'output.yaml'
    main(base_url, yaml_output_path)