"""
Tests for Validation Tools
==========================
"""

import pytest
import json


class TestValidateEvidenceItem:
    """Test evidence item validation."""
    
    def test_valid_complete_item(self):
        """Test validation of a complete valid item."""
        from tools.validation_tools import validate_evidence_item
        import asyncio
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            "disease_name": "Non-Small Cell Lung Cancer",
            "evidence_type": "PREDICTIVE",
            "evidence_level": "B",
            "evidence_direction": "SUPPORTS",
            "evidence_significance": "SENSITIVITY",
            "evidence_description": "Patients with EGFR L858R showed 71% response to erlotinib.",
            "therapy_names": "Erlotinib"
        }
        
        result = asyncio.run(validate_evidence_item({"item": item}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_valid"] == True
        assert content["error_count"] == 0
    
    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        from tools.validation_tools import validate_evidence_item
        import asyncio
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            # Missing: disease_name, evidence_type, etc.
        }
        
        result = asyncio.run(validate_evidence_item({"item": item}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_valid"] == False
        assert content["error_count"] > 0
        assert any("Missing required field" in e for e in content["errors"])
    
    def test_invalid_evidence_type(self):
        """Test validation catches invalid evidence type."""
        from tools.validation_tools import validate_evidence_item
        import asyncio
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            "disease_name": "Lung Cancer",
            "evidence_type": "INVALID_TYPE",  # Invalid
            "evidence_level": "B",
            "evidence_direction": "SUPPORTS",
            "evidence_significance": "SENSITIVITY",
            "evidence_description": "Test description"
        }
        
        result = asyncio.run(validate_evidence_item({"item": item}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_valid"] == False
        assert any("Invalid evidence_type" in e for e in content["errors"])
    
    def test_predictive_requires_therapy(self):
        """Test that PREDICTIVE evidence requires therapy_names."""
        from tools.validation_tools import validate_evidence_item
        import asyncio
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            "disease_name": "Lung Cancer",
            "evidence_type": "PREDICTIVE",
            "evidence_level": "B",
            "evidence_direction": "SUPPORTS",
            "evidence_significance": "SENSITIVITY",
            "evidence_description": "Test description",
            # Missing: therapy_names
        }
        
        result = asyncio.run(validate_evidence_item({"item": item}))
        content = json.loads(result["content"][0]["text"])
        
        assert any("PREDICTIVE evidence requires therapy_names" in e for e in content["errors"])
    
    def test_generic_therapy_warning(self):
        """Test warning for generic therapy names."""
        from tools.validation_tools import validate_evidence_item
        import asyncio
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            "disease_name": "Lung Cancer",
            "evidence_type": "PREDICTIVE",
            "evidence_level": "B",
            "evidence_direction": "SUPPORTS",
            "evidence_significance": "SENSITIVITY",
            "evidence_description": "Test description",
            "therapy_names": "TKIs"  # Too generic
        }
        
        result = asyncio.run(validate_evidence_item({"item": item}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["warning_count"] > 0
        assert any("too generic" in w for w in content["warnings"])


class TestCheckActionability:
    """Test actionability checking."""
    
    def test_actionable_claim(self):
        """Test that actionable claims are recognized."""
        from tools.validation_tools import check_actionability
        import asyncio
        
        claim = "Patients with EGFR L858R mutation showed improved response to erlotinib treatment with 71% response rate."
        
        result = asyncio.run(check_actionability({"claim": claim}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_actionable"] == True
        assert content["checklist"]["has_specific_variant"] == True
        assert content["checklist"]["has_clinical_outcome"] == True
    
    def test_prevalence_not_actionable(self):
        """Test that prevalence statistics alone are not actionable."""
        from tools.validation_tools import check_actionability
        import asyncio
        
        claim = "EGFR mutations are found in 30% of lung cancer patients."
        
        result = asyncio.run(check_actionability({"claim": claim}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_actionable"] == False
        assert content["checklist"]["is_not_just_prevalence"] == False
    
    def test_mechanism_not_actionable(self):
        """Test that mechanism descriptions alone are not actionable."""
        from tools.validation_tools import check_actionability
        import asyncio
        
        claim = "The V600E mutation activates the MAPK pathway by phosphorylating MEK."
        
        result = asyncio.run(check_actionability({"claim": claim}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["is_actionable"] == False


class TestFieldDefinitions:
    """Test field definition constants."""
    
    def test_tier1_field_count(self):
        """Test that Tier 1 has 25 fields."""
        from schemas import TIER_1_FIELDS
        assert len(TIER_1_FIELDS) == 25
    
    def test_tier2_field_count(self):
        """Test that Tier 2 has 20 fields."""
        from schemas import TIER_2_FIELDS
        assert len(TIER_2_FIELDS) == 20
    
    def test_required_fields_subset(self):
        """Test that required fields are subset of Tier 1."""
        from schemas import TIER_1_FIELDS, REQUIRED_FIELDS
        
        for field in REQUIRED_FIELDS:
            assert field in TIER_1_FIELDS, f"{field} not in TIER_1_FIELDS"
    
    def test_evidence_significance_completeness(self):
        """Test that all evidence types have significance values."""
        from schemas import VALID_EVIDENCE_TYPES, EVIDENCE_SIGNIFICANCE_MAP
        
        for etype in VALID_EVIDENCE_TYPES:
            assert etype in EVIDENCE_SIGNIFICANCE_MAP, f"{etype} missing from EVIDENCE_SIGNIFICANCE_MAP"
            assert len(EVIDENCE_SIGNIFICANCE_MAP[etype]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])