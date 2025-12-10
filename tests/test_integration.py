"""
Integration Tests
=================

End-to-end tests for the extraction system.
These tests require actual paper data and may be slow.
"""

import pytest
import json
from pathlib import Path


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestContextIntegration:
    """Test context with real data."""
    
    @pytest.fixture
    def context(self):
        """Create a context for testing."""
        from context import CIViCContext
        ctx = CIViCContext()
        return ctx
    
    def test_load_ground_truth(self, context):
        """Test loading ground truth database."""
        try:
            context.load_ground_truth()
            assert context.ground_truth_df is not None
            assert len(context.ground_truth_df) > 0
        except FileNotFoundError:
            pytest.skip("Ground truth file not available")
    
    def test_get_ground_truth_for_paper(self, context):
        """Test getting ground truth for a specific paper."""
        try:
            context.load_ground_truth()
            
            # Get a paper ID that exists
            if context.ground_truth_df is not None:
                paper_id = context.ground_truth_df["paper_folder"].iloc[0]
                items = context.get_ground_truth_for_paper(paper_id)
                
                assert isinstance(items, list)
                assert len(items) > 0
        except FileNotFoundError:
            pytest.skip("Ground truth file not available")


class TestNormalizationIntegration:
    """Test normalization with real API calls."""
    
    def test_full_item_normalization(self):
        """Test normalizing a complete evidence item."""
        from normalization import EvidenceNormalizer
        
        normalizer = EvidenceNormalizer()
        
        item = {
            "feature_names": "EGFR",
            "variant_names": "L858R",
            "disease_name": "Non-Small Cell Lung Cancer",
            "therapy_names": "Erlotinib",
            "evidence_type": "PREDICTIVE",
            "evidence_level": "B",
            "evidence_direction": "SUPPORTS",
            "evidence_significance": "SENSITIVITY",
            "evidence_description": "Test item"
        }
        
        result = normalizer.normalize_item(item)
        
        # Check result structure
        assert result.normalized_item is not None
        assert "_normalization" in result.normalized_item
        
        # May have errors due to API issues, but should complete
        assert isinstance(result.fields_added, list)
    
    def test_variant_annotation(self):
        """Test variant annotation."""
        from normalization import VariantAnnotator
        
        annotator = VariantAnnotator()
        
        # Test well-known variant
        result = annotator.annotate("BRAF", "V600E")
        
        # Check structure - may not find due to API issues
        assert hasattr(result, "found")
        assert hasattr(result, "gene")
        assert result.gene == "BRAF"
        assert result.variant == "V600E"


class TestToolsIntegration:
    """Test tools with real context."""
    
    @pytest.fixture
    def setup_context(self):
        """Set up context for tool testing."""
        from context import CIViCContext, set_current_context
        
        ctx = CIViCContext()
        set_current_context(ctx)
        return ctx
    
    def test_full_extraction_workflow(self, setup_context):
        """Test a simulated extraction workflow."""
        from tools.extraction_tools import (
            save_extraction_plan,
            save_evidence_items,
            save_critique,
            get_draft_extractions
        )
        from tools.normalization_tools import normalize_extractions, finalize_extraction
        import asyncio
        
        ctx = setup_context
        
        # Step 1: Save plan
        plan_result = asyncio.run(save_extraction_plan({
            "paper_type": "PRIMARY",
            "expected_items": 1,
            "key_variants": ["EGFR L858R"],
            "key_therapies": ["Erlotinib"],
            "key_diseases": ["Lung Cancer"],
            "focus_sections": ["Results"],
            "extraction_notes": "Test"
        }))
        assert "Plan saved" in plan_result["content"][0]["text"]
        
        # Step 2: Save items
        items_result = asyncio.run(save_evidence_items({
            "items": [{
                "feature_names": "EGFR",
                "variant_names": "L858R",
                "disease_name": "Lung Cancer",
                "evidence_type": "PREDICTIVE",
                "evidence_level": "B",
                "evidence_direction": "SUPPORTS",
                "evidence_significance": "SENSITIVITY",
                "evidence_description": "Test finding",
                "therapy_names": "Erlotinib"
            }]
        }))
        content = json.loads(items_result["content"][0]["text"])
        assert content["saved"] == 1
        
        # Step 3: Get drafts
        drafts_result = asyncio.run(get_draft_extractions({}))
        drafts = json.loads(drafts_result["content"][0]["text"])
        assert drafts["count"] == 1
        
        # Step 4: Save critique (approve)
        critique_result = asyncio.run(save_critique({
            "overall_assessment": "APPROVE",
            "item_feedback": [],
            "missing_items": [],
            "extra_items": [],
            "summary": "Looks good"
        }))
        critique = json.loads(critique_result["content"][0]["text"])
        assert critique["recommendation"] == "FINALIZE"
        
        # Step 5: Normalize (may fail due to API)
        try:
            norm_result = asyncio.run(normalize_extractions({}))
            # Just check it ran
            assert "content" in norm_result
        except Exception:
            pass  # API may be unavailable
        
        # Step 6: Finalize
        final_result = asyncio.run(finalize_extraction({}))
        final = json.loads(final_result["content"][0]["text"])
        assert final["success"] == True
        assert final["items_extracted"] == 1
        assert ctx.state.is_complete == True


class TestHooksIntegration:
    """Test hooks functionality."""
    
    def test_ground_truth_blocking(self):
        """Test that ground truth is blocked during extraction."""
        from hooks import set_ground_truth_access, block_ground_truth
        from claude_agent_sdk import HookContext
        import asyncio
        
        # Block ground truth
        set_ground_truth_access(False)
        
        input_data = {
            "tool_name": "lookup_ground_truth"
        }
        
        result = asyncio.run(block_ground_truth(input_data, None, HookContext()))
        
        # Should block
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    
    def test_ground_truth_allowed_in_evaluation(self):
        """Test that ground truth is allowed during evaluation."""
        from hooks import set_ground_truth_access, block_ground_truth
        from claude_agent_sdk import HookContext
        import asyncio
        
        # Allow ground truth
        set_ground_truth_access(True)
        
        input_data = {
            "tool_name": "lookup_ground_truth"
        }
        
        result = asyncio.run(block_ground_truth(input_data, None, HookContext()))
        
        # Should allow (empty result)
        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])