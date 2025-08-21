import json
from pathlib import Path


def get_data_contract_specs(contract_directory):
    contract_specs = {}
    
    contract_dir = Path(contract_directory)
    for file_path in contract_dir.glob("*.json"):
        with open(file_path, 'r') as file:
            contract_spec = json.load(file)
            contract_name = file_path.stem
            contract_specs[contract_name] = contract_spec
            
    return contract_specs