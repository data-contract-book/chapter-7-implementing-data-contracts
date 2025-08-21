import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from data_contract_components.detection._get_data_catalog import get_data_catalog
from data_contract_components.detection._get_data_contract_specs import get_data_contract_specs


class ContractViolationDetector:
    """
    A class to detect contract constraint violations by comparing contract specifications
    against the actual data catalog schema and constraints.
    
    This class validates that the actual database schema matches the constraints
    defined in the contract specifications.
    """
    
    def __init__(self, contract_directory: str) -> None:
        """
        Initialize the ContractViolationDetector.
        
        Args:
            contract_directory: Path to the directory containing contract specification JSON files
        """
        self.contract_directory = Path(contract_directory)
    
    def _values_equal(self, val1: Any, val2: Any) -> bool:
        """
        Compare two values, handling NaN properly using pandas equality.
        
        Args:
            val1: First value to compare
            val2: Second value to compare
            
        Returns:
            True if values are equal (including NaN == NaN), False otherwise
        """
        return pd.Series([val1]).equals(pd.Series([val2]))
    
    def transform_contract_specs_to_catalog_format(self) -> List[Dict[str, Any]]:
        """
        Transform contract specifications to match the data catalog format for comparison.
        
        Returns:
            List of dictionaries containing contract constraints in catalog format
        """
        contract_specs = get_data_contract_specs(self.contract_directory)
        catalog_format_specs = []
        
        for contract_name, contract_spec in contract_specs.items():
            schema = contract_spec["schema"]
            table_catalog = schema["table_catalog"]
            table_schema = schema["table_schema"]
            table_name = schema["table_name"]
            properties = schema["properties"]
            
            for column_name, column_spec in properties.items():
                constraint = column_spec["constraints"]
                
                catalog_format_specs.append({
                    "contract_name": contract_name,
                    "table_catalog": table_catalog,
                    "table_schema": table_schema,
                    "table_name": table_name,
                    "column_name": column_name,
                    "is_nullable": "NO" if constraint.get("is_nullable", True) == False else "YES",
                    "data_type": constraint.get("data_type"),
                    "character_maximum_length": constraint.get("character_maximum_length"),
                    "numeric_precision": constraint.get("numeric_precision"),
                    "datetime_precision": constraint.get("datetime_precision"),
                    "is_updatable": "YES" if constraint.get("is_updatable", True) else "NO",
                    "constraint_type": "PRIMARY KEY" if constraint.get("primaryKey", False) else None,
                    "element_data_type": column_spec.get("array_element", {}).get("data_type"),
                    "element_character_maximum_length": column_spec.get("array_element", {}).get("character_maximum_length"),
                    "element_numeric_precision": column_spec.get("array_element", {}).get("numeric_precision"),
                    "element_datetime_precision": column_spec.get("array_element", {}).get("datetime_precision"),
                })
                
        return catalog_format_specs
    
    def detect_constraint_violations(self) -> List[Dict[str, str]]:
        """
        Detect constraint violations by comparing contract specifications with the data catalog.
        
        Returns:
            List of dictionaries containing violation details. Each dictionary has keys:
            - contract_name: Name of the contract with violations
            - table_name: Name of the table with violations
            - column_name: Name of the column with violations
            - violations: String describing the specific violation
        """
        contract_specs_df = pd.DataFrame(self.transform_contract_specs_to_catalog_format())
        catalog_df = get_data_catalog()
        
        merged = contract_specs_df.merge(
            catalog_df,
            on=['table_catalog', 'table_schema', 'table_name', 'column_name'],
            how='left',
            suffixes=('_contract', '_catalog'),
            indicator=True
        )
        
        violations = []
        
        # Check for missing columns in data catalog
        missing_columns = merged[merged['_merge'] == 'left_only']
        for row in missing_columns.itertuples():
            violations.append({
                "contract_name": row.contract_name,
                "table_name": row.table_name,
                "column_name": row.column_name,
                "violations": f"Column '{row.column_name}' is defined in contract but missing from data catalog"
            })
        
        # Check for constraint violations on existing columns
        existing_columns = merged[merged['_merge'] == 'both']
        
        # Define fields to check for violations
        constraint_fields = [
            'constraint_type',
            'data_type', 
            'is_nullable',
            'numeric_precision',
            'datetime_precision',
            'character_maximum_length',
            'is_updatable',
            'element_data_type',
            'element_character_maximum_length',
            'element_numeric_precision',
            'element_datetime_precision'
        ]
        
        for violation in existing_columns.itertuples():
            violations_found = []
            
            for field in constraint_fields:
                contract_field = f'{field}_contract'
                catalog_field = f'{field}_catalog'
                
                contract_value = getattr(violation, contract_field)
                catalog_value = getattr(violation, catalog_field)
                
                # Skip if contract doesn't specify this constraint
                if contract_value is None or pd.isna(contract_value):
                    continue
                
                # Check if values are different
                if not self._values_equal(contract_value, catalog_value):
                    violations_found.append(f"{field.replace('_', ' ').title()}: expected {contract_value}, found {catalog_value}")
            
            if violations_found:
                for violation_detail in violations_found:
                    violations.append({
                        "contract_name": violation.contract_name,
                        "table_name": violation.table_name,
                        "column_name": violation.column_name,
                        "violations": violation_detail
                    })
        
        return violations
