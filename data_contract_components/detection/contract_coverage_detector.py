import pandas as pd
from pathlib import Path
from typing import Dict, List
from data_contract_components.detection._get_data_catalog import get_data_catalog
from data_contract_components.detection._get_data_contract_specs import get_data_contract_specs


class ContractCoverageDetector:
    """
    A class to detect contract coverage by comparing contract specifications
    against the actual data catalog.
    
    This class loads contract specification files and checks if the tables
    defined in those contracts are present in the data catalog.
    """
    
    def __init__(self, contract_directory: str) -> None:
        """
        Initialize the ContractCoverageDetector.
        
        Args:
            contract_directory: Path to the directory containing contract specification JSON files
        """
        self.contract_directory = Path(contract_directory)
    
    def get_contract_spec_coverage(self) -> List[Dict[str, str]]:
        """
        Extract table coverage information from all contract specifications.
        
        Returns:
            List of dictionaries containing contract name and table information
            (table_catalog, table_schema, table_name)
        """
        contract_specs = get_data_contract_specs(self.contract_directory)
        coverage = []
        
        for contract_name, contract_spec in contract_specs.items():
            schema = contract_spec.get("schema", {})
            coverage.append({
                "contract_name": contract_name,
                "table_catalog": schema.get("table_catalog"),
                "table_schema": schema.get("table_schema"),
                "table_name": schema.get("table_name")
            })
                
        return coverage
    
    def detect_coverage_in_data_catalog(self) -> List[str]:
        """
        Check which contract-covered tables are missing from the data catalog.
        
        Returns:
            List of table names that are under contract but missing from the data catalog
        """
        coverage = self.get_contract_spec_coverage()
        coverage_df = pd.DataFrame(coverage)  
        catalog_df = get_data_catalog()
        
        merged = coverage_df.merge(
            catalog_df, 
            on=['table_catalog', 'table_schema', 'table_name'], 
            how='left', 
            indicator=True
        )
        
        missing_assets_df = merged[merged['_merge'] == 'left_only']
        missing_table_names = missing_assets_df['table_name'].tolist()
        
        return missing_table_names