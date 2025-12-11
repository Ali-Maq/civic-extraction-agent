"""
Tests for MCP Tools
===================
"""

import pytest
import json


class TestExtractionTools:
    """Test extraction state management tools."""
    
    def test_save_and_get_extraction_plan(self):
        """Test saving and retrieving extraction plan."""
        from context import CIViCContext, set_current_context
        from tools.extraction_tools import save_extraction_plan, get_extraction_plan
        import asyncio
        
        # Setup context
        ctx = CIViCContext()
        set_current_context(ctx)
        
        # Save plan
        plan_args = {
            "paper_type": "PRIMARY",
            "expected_items": 3,
            "key_variants": ["EGFR L858R", "EGFR T790M"],
            "key_therapies": ["Erlotinib", "Osimertinib"],
            "key_diseases": ["Non-Small Cell Lung Cancer"],
            "focus_sections": ["Results", "Tables"],
            "extraction_notes": "Phase III trial"
        }
        
        result = asyncio.run(save_extraction_plan.handler(plan_args))
        assert "Plan saved" in result["content"][0]["text"]
        
        # Get plan
        result = asyncio.run(get_extraction_plan.handler({}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["paper_type"] == "PRIMARY"
        assert content["expected_items"] == 3
    
    def test_save_evidence_items(self):
        """Test saving evidence items."""
        from context import CIViCContext, set_current_context
        from tools.extraction_tools import save_evidence_items
        import asyncio
        
        # Setup context
        ctx = CIViCContext()
        set_current_context(ctx)
        
        items = [
            {
                "feature_names": "EGFR",
                "variant_names": "L858R",
                "disease_name": "Lung Cancer",
                "evidence_type": "PREDICTIVE",
                "evidence_level": "B",
                "evidence_direction": "SUPPORTS",
                "evidence_significance": "SENSITIVITY",
                "evidence_description": "Test"
            }
        ]
        
        result = asyncio.run(save_evidence_items.handler({"items": items}))
        content = json.loads(result["content"][0]["text"])
        
        assert content["saved"] == 1
        assert ctx.state.draft_extractions == items
    
    def test_save_critique(self):
        """Test saving critique."""
        from context import CIViCContext, set_current_context
        from tools.extraction_tools import save_critique
        import asyncio
        
        # Setup context
        ctx = CIViCContext()
        ctx.state.max_iterations = 3
        ctx.state.iteration_count = 1
        set_current_context(ctx)
        
        critique_args = {
            "overall_assessment": "NEEDS_REVISION",
            "item_feedback": [{"index": 0, "feedback": "Fix therapy name"}],
            "missing_items": [],
            "extra_items": [],
            "summary": "Minor fixes needed"
        }
        
        result = asyncio.run(save_critique.handler(critique_args))
        content = json.loads(result["content"][0]["text"])
        
        assert content["assessment"] == "NEEDS_REVISION"
        assert content["needs_revision"] == True
        assert content["can_iterate"] == True
        assert content["recommendation"] == "ITERATE"


class TestNormalizationTools:
    """Test normalization tools."""
    
    def test_gene_lookup(self):
        """Test gene Entrez ID lookup."""
        from tools.normalization_tools import lookup_gene_entrez
        import asyncio
        
        # Test tool handler
        result = asyncio.run(lookup_gene_entrez.handler({"gene_symbol": "EGFR"}))
        content = json.loads(result["content"][0]["text"])
        
        # May fail if API is down, so check structure
        assert "found" in content
        if content["found"]:
            assert content["gene_entrez_id"] == "1956"  # EGFR Entrez ID
    
    def test_disease_lookup(self):
        """Test disease DOID lookup."""
        from tools.normalization_tools import lookup_disease_doid_tool
        import asyncio
        
        result = asyncio.run(lookup_disease_doid_tool.handler({"disease_name": "lung cancer"}))
        content = json.loads(result["content"][0]["text"])
        
        assert "found" in content
        if content["found"]:
            assert "DOID" in content.get("disease_doid", "")
    
    def test_normalize_evidence_item(self):
        """Test normalizing a single evidence item."""
        from tools.normalization_tools import normalize_evidence_item_async
        import asyncio
        
        item = {
            "feature_names": "BRAF",
            "variant_names": "V600E",
            "disease_name": "melanoma",
            "therapy_names": "Vemurafenib"
        }
        
        normalized = asyncio.run(normalize_evidence_item_async(item))
        
        # Check normalization metadata was added
        assert "_normalization" in normalized
        assert normalized["_normalization"]["normalized"] == True


class TestContextManagement:
    """Test context management."""
    
    def test_set_get_context(self):
        """Test setting and getting context."""
        from context import CIViCContext, set_current_context, get_current_context
        
        ctx = CIViCContext()
        set_current_context(ctx)
        
        retrieved = get_current_context()
        assert retrieved is ctx
    
    def test_require_context_raises(self):
        """Test that require_context raises when no context."""
        from context import set_current_context, require_context
        
        # Clear context
        set_current_context(None)
        
        with pytest.raises(RuntimeError):
            require_context()
    
    def test_extraction_state_reset(self):
        """Test extraction state reset."""
        from context.state import ExtractionState, ExtractionPlan
        
        state = ExtractionState()
        state.extraction_plan = ExtractionPlan(
            paper_type="PRIMARY", 
            expected_items=1,
            key_variants=[],
            key_therapies=[],
            key_diseases=[],
            focus_sections=[],
            extraction_notes=""
        )
        state.draft_extractions = [{"test": "item"}]
        state.iteration_count = 2
        
        state.reset()
        
        assert state.extraction_plan is None
        assert state.draft_extractions == []
        assert state.iteration_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])