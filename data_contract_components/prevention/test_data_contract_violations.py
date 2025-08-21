import unittest
from data_contract_components.detection.contract_coverage_detector import ContractCoverageDetector
from data_contract_components.detection.contract_violation_detector import ContractViolationDetector


class TestContractViolations(unittest.TestCase):
    def setUp(self):
        self.contract_coverage_detector = ContractCoverageDetector("data_contract_components/contract_definition")
        self.contract_violation_detector = ContractViolationDetector("data_contract_components/contract_definition")

    def test_all_contract_assets_present_in_catalog(self):
        """Test that all assets under contract are present in the data catalog"""
        missing_table_names = self.contract_coverage_detector.detect_coverage_in_data_catalog()

        self.assertTrue(len(missing_table_names) == 0, f"All assets under contract should be present in data catalog.\nMissing: {missing_table_names}")

    def test_data_contracts_against_data_catalog(self):
        """Test that all data contract constraints match the data catalog."""
        violations = self.contract_violation_detector.detect_constraint_violations()

        if violations:
            violation_lines = []
            for i, violation in enumerate(violations, 1):
                violation_lines.append(f"{i}. Contract: {violation.get('contract_name', 'N/A')}")
                violation_lines.append(f"   Table: {violation.get('table_name', 'N/A')}")
                violation_lines.append(f"   Column: {violation.get('column_name', 'N/A')}")
                violation_lines.append(f"   Issue: {violation.get('violations', 'N/A')}")
                violation_lines.append("")  # Empty line between violations
            violation_text = "\n".join(violation_lines)
            self.fail(f"All data contract constraints should match the data catalog.\n\nViolations:\n{violation_text}")
        else:
            self.assertTrue(True)
