"""Unit tests for project_structure_parser.

Tests the project structure parsing, serialization, and update functionality:
- Parsing markdown with embedded project structure
- Serializing structure back to markdown format
- Updating Definition of Done checkboxes
- Updating frontmatter timestamps

References:
- https://docs.python.org/3/library/dataclasses.html
- https://docs.python.org/3/library/re.html
"""


import pytest

from collab_sims.core.loaders.project_structure_parser import (
    Activity,
    ActivityResult,
    DefinitionOfDoneItem,
    ProjectStructure,
    Stage,
    parse_project_structure,
    serialize_project_structure,
    update_dod_checkbox,
    update_frontmatter_timestamp,
)


class TestParseProjectStructure:
    """Tests for parse_project_structure function."""

    def test_parse_empty_structure(self):
        """Test parsing markdown with no process structure."""
        markdown = """---
title: Test Project
---

# Test Project

Some content here.
"""
        structure = parse_project_structure(markdown)

        assert structure is not None
        assert len(structure.stages) == 0

    def test_parse_single_stage_with_activity(self):
        """Test parsing markdown with one stage and one activity."""
        markdown = """---
title: Test Project
---

# Test Project

## Process Structure

### Stage 1: Planning
**Description:** Initial planning phase

#### Activity: Create Plan
**ID:** activity-plan
**Required:** Yes
**Path:** activities/plan.md
**Description:** Create project plan

**Definition of Done:**
- [ ] Plan document created

**Activity Results:** (none yet)

---
"""
        structure = parse_project_structure(markdown)

        assert len(structure.stages) == 1
        stage = structure.stages[0]
        assert stage.title == "Planning"
        assert stage.description == "Initial planning phase"
        assert len(stage.activities) == 1

        activity = stage.activities[0]
        assert activity.id == "activity-plan"
        assert activity.title == "Create Plan"
        assert activity.required is True
        assert activity.path == "activities/plan.md"
        assert activity.description == "Create project plan"
        assert len(activity.definition_of_done) == 1
        assert activity.definition_of_done[0].text == "Plan document created"
        assert activity.definition_of_done[0].checked is False

    def test_parse_multiple_stages(self):
        """Test parsing markdown with multiple stages and activities."""
        markdown = """---
title: Test Project
---

## Process Structure

### Stage 1: Understand
**Description:** Understanding phase

#### Activity: Research
**ID:** activity-research
**Required:** Yes
**Path:** activities/research.md
**Description:** Research the problem

**Definition of Done:**
- [ ] Research complete

**Activity Results:** (none yet)

---

#### Activity: Analyze
**ID:** activity-analyze
**Required:** No
**Path:** activities/analyze.md
**Description:** Analyze findings

**Definition of Done:**
- [ ] Analysis complete

**Activity Results:** (none yet)

---

### Stage 2: Execute
**Description:** Execution phase

#### Activity: Build
**ID:** activity-build
**Required:** Yes
**Path:** activities/build.md
**Description:** Build the solution

**Definition of Done:**
- [ ] Solution built

**Activity Results:** (none yet)

---
"""
        structure = parse_project_structure(markdown)

        assert len(structure.stages) == 2

        # Verify first stage
        stage1 = structure.stages[0]
        assert stage1.title == "Understand"
        assert len(stage1.activities) == 2
        assert stage1.activities[0].title == "Research"
        assert stage1.activities[0].required is True
        assert stage1.activities[1].title == "Analyze"
        assert stage1.activities[1].required is False

        # Verify second stage
        stage2 = structure.stages[1]
        assert stage2.title == "Execute"
        assert len(stage2.activities) == 1
        assert stage2.activities[0].title == "Build"
        assert len(stage2.activities[0].definition_of_done) == 1

    def test_parse_activity_with_results(self):
        """Test parsing activity with result files listed."""
        markdown = """---
title: Test Project
---

## Process Structure

### Stage 1: Test
**Description:** Test stage

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** activities/test.md
**Description:** Test activity

**Definition of Done:**
- [x] Task done

**Activity Results:**
- result_v01.md (2025-01-15)

---
"""
        structure = parse_project_structure(markdown)

        activity = structure.stages[0].activities[0]
        assert len(activity.activity_results) == 1
        assert activity.activity_results[0].filename == "result_v01.md"
        assert activity.activity_results[0].date == "2025-01-15"


class TestSerializeProjectStructure:
    """Tests for serialize_project_structure function."""

    def test_serialize_empty_structure(self):
        """Test serializing an empty structure."""
        structure = ProjectStructure()
        markdown = serialize_project_structure(structure)

        assert "## Process Structure" in markdown
        assert "### Stage" not in markdown

    def test_serialize_single_stage(self):
        """Test serializing a structure with one stage."""
        structure = ProjectStructure()
        stage = Stage(
            id="stage-1",
            title="Planning",
            description="Planning phase"
        )
        activity = Activity(
            id="activity-1",
            title="Create Plan",
            required=True,
            path="activities/plan.md",
            description="Create the plan"
        )
        activity.definition_of_done = [
            DefinitionOfDoneItem(text="Plan created", checked=False),
            DefinitionOfDoneItem(text="Plan reviewed", checked=True),
        ]
        stage.activities.append(activity)
        structure.stages.append(stage)

        markdown = serialize_project_structure(structure)

        assert "## Process Structure" in markdown
        assert "### Stage 1: Planning" in markdown
        assert "**Description:** Planning phase" in markdown
        assert "#### Activity: Create Plan" in markdown
        assert "**ID:** activity-1" in markdown
        assert "**Required:** Yes" in markdown
        assert "**Path:** activities/plan.md" in markdown
        assert "**Definition of Done:**" in markdown
        assert "- [ ] Plan created" in markdown
        assert "- [x] Plan reviewed" in markdown

    def test_serialize_multiple_stages(self):
        """Test serializing structure with multiple stages."""
        structure = ProjectStructure()

        # Add two stages with activities
        for i in range(1, 3):
            stage = Stage(
                id=f"stage-{i}",
                title=f"Stage {i}",
                description=f"Stage {i} description"
            )
            activity = Activity(
                id=f"activity-{i}",
                title=f"Activity {i}",
                required=i == 1,
                path=f"activities/act{i}.md",
                description=f"Activity {i} desc"
            )
            stage.activities.append(activity)
            structure.stages.append(stage)

        markdown = serialize_project_structure(structure)

        assert "### Stage 1: Stage 1" in markdown
        assert "### Stage 2: Stage 2" in markdown
        assert "**Required:** Yes" in markdown
        assert "**Required:** No" in markdown

    def test_serialize_with_activity_results(self):
        """Test serializing activity with results."""
        structure = ProjectStructure()
        stage = Stage(id="stage-1", title="Test", description="Test stage")
        activity = Activity(
            id="activity-1",
            title="Test Activity",
            required=True,
            path="activities/test.md",
            description="Test"
        )
        activity.activity_results = [
            ActivityResult(filename="result_v01.md", date="2025-01-15"),
            ActivityResult(filename="result_v02.md", date="2025-01-16"),
        ]
        stage.activities.append(activity)
        structure.stages.append(stage)

        markdown = serialize_project_structure(structure)

        assert "**Activity Results:**" in markdown
        assert "- result_v01.md (2025-01-15)" in markdown
        assert "- result_v02.md (2025-01-16)" in markdown


class TestUpdateDoDCheckbox:
    """Tests for update_dod_checkbox function."""

    def test_update_unchecked_to_checked(self):
        """Test checking an unchecked item."""
        markdown = """---
title: Test
---

## Process Structure

### Stage 1: Test
**Description:** Test

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** test.md
**Description:** Test

**Definition of Done:**
- [ ] Item 1
- [ ] Item 2

---
"""
        updated = update_dod_checkbox(
            markdown_content=markdown,
            stage_id="stage-test",
            activity_id="activity-test",
            item_index=0,
            checked=True
        )

        assert "- [x] Item 1" in updated
        assert "- [ ] Item 2" in updated

    def test_update_checked_to_unchecked(self):
        """Test unchecking a checked item."""
        markdown = """---
title: Test
---

## Process Structure

### Stage 1: Test
**Description:** Test

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** test.md
**Description:** Test

**Definition of Done:**
- [x] Item 1
- [ ] Item 2

---
"""
        updated = update_dod_checkbox(
            markdown_content=markdown,
            stage_id="stage-test",
            activity_id="activity-test",
            item_index=0,
            checked=False
        )

        assert "- [ ] Item 1" in updated
        assert "- [ ] Item 2" in updated

    def test_roundtrip_preserves_checkboxes(self):
        """Test that serialize->parse->serialize preserves DoD checkboxes."""
        # Create structure with multiple DoD items
        structure = ProjectStructure()
        stage = Stage(id="stage-test", title="Test", description="Test")
        activity = Activity(
            id="activity-test",
            title="Test Activity",
            required=True,
            path="test.md",
            description="Test"
        )
        activity.definition_of_done = [
            DefinitionOfDoneItem(text="Item 1", checked=False),
            DefinitionOfDoneItem(text="Item 2", checked=True),
            DefinitionOfDoneItem(text="Item 3", checked=False),
        ]
        stage.activities.append(activity)
        structure.stages.append(stage)

        # Serialize
        markdown1 = serialize_project_structure(structure)

        # Parse
        parsed = parse_project_structure(markdown1)

        # Serialize again
        markdown2 = serialize_project_structure(parsed)

        # Should be identical
        assert markdown1 == markdown2
        assert "- [ ] Item 1" in markdown2
        assert "- [x] Item 2" in markdown2
        assert "- [ ] Item 3" in markdown2

    def test_invalid_stage_id(self):
        """Test error handling for invalid stage ID."""
        markdown = """---
title: Test
---

## Process Structure

### Stage 1: Test
**Description:** Test

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** test.md
**Description:** Test

**Definition of Done:**
- [ ] Item 1

---
"""
        with pytest.raises(ValueError, match="Stage.*not found"):
            update_dod_checkbox(
                markdown_content=markdown,
                stage_id="stage-nonexistent",
                activity_id="activity-test",
                item_index=0,
                checked=True
            )

    def test_invalid_activity_id(self):
        """Test error handling for invalid activity ID."""
        markdown = """---
title: Test
---

## Process Structure

### Stage 1: Test
**Description:** Test

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** test.md
**Description:** Test

**Definition of Done:**
- [ ] Item 1

---
"""
        with pytest.raises(ValueError, match="Activity.*not found"):
            update_dod_checkbox(
                markdown_content=markdown,
                stage_id="stage-test",
                activity_id="activity-nonexistent",
                item_index=0,
                checked=True
            )

    def test_invalid_item_index(self):
        """Test error handling for invalid item index."""
        markdown = """---
title: Test
---

## Process Structure

### Stage 1: Test
**Description:** Test

#### Activity: Test Activity
**ID:** activity-test
**Required:** Yes
**Path:** test.md
**Description:** Test

**Definition of Done:**
- [ ] Item 1

---
"""
        with pytest.raises(ValueError, match="out of range"):
            update_dod_checkbox(
                markdown_content=markdown,
                stage_id="stage-test",
                activity_id="activity-test",
                item_index=5,
                checked=True
            )


class TestUpdateFrontmatterTimestamp:
    """Tests for update_frontmatter_timestamp function."""

    def test_update_existing_timestamp(self):
        """Test updating an existing updated_at timestamp."""
        markdown = """---
title: Test Project
created_at: 2025-01-01
updated_at: 2025-01-01T12:00:00Z
---

Content here.
"""
        updated = update_frontmatter_timestamp(markdown)

        assert "updated_at:" in updated
        assert "2025-01-01T12:00:00Z" not in updated
        # Verify new timestamp is in ISO format with Z
        assert "Z" in updated
        assert "updated_at: 20" in updated

    def test_add_timestamp_when_missing(self):
        """Test adding updated_at when it doesn't exist."""
        markdown = """---
title: Test Project
created_at: 2025-01-01
---

Content here.
"""
        updated = update_frontmatter_timestamp(markdown)

        assert "updated_at:" in updated
        assert "Z" in updated

    def test_no_frontmatter(self):
        """Test handling markdown without frontmatter."""
        markdown = """# Test Project

Content here.
"""
        updated = update_frontmatter_timestamp(markdown)

        # Should return content unchanged
        assert updated == markdown


class TestProjectStructureToDict:
    """Tests for ProjectStructure.to_dict() method."""

    def test_empty_structure_to_dict(self):
        """Test converting empty structure to dictionary."""
        structure = ProjectStructure()
        result = structure.to_dict()

        assert "stages" in result
        assert len(result["stages"]) == 0

    def test_structure_with_data_to_dict(self):
        """Test converting populated structure to dictionary."""
        structure = ProjectStructure()
        stage = Stage(id="stage-1", title="Test", description="Test stage")
        activity = Activity(
            id="activity-1",
            title="Test Activity",
            required=True,
            path="test.md",
            description="Test activity"
        )
        activity.definition_of_done = [
            DefinitionOfDoneItem(text="Item 1", checked=True),
        ]
        activity.activity_results = [
            ActivityResult(filename="result.md", date="2025-01-15"),
        ]
        stage.activities.append(activity)
        structure.stages.append(stage)

        result = structure.to_dict()

        assert len(result["stages"]) == 1
        assert result["stages"][0]["id"] == "stage-1"
        assert result["stages"][0]["title"] == "Test"
        assert result["stages"][0]["completion_count"] == 1
        assert result["stages"][0]["total_activities"] == 1

        act = result["stages"][0]["activities"][0]
        assert act["id"] == "activity-1"
        assert act["title"] == "Test Activity"
        assert act["required"] is True
        assert act["completed"] is True
        assert len(act["definition_of_done"]) == 1
        assert act["definition_of_done"][0]["text"] == "Item 1"
        assert act["definition_of_done"][0]["checked"] is True
        assert len(act["activity_results"]) == 1
        assert act["activity_results"][0]["filename"] == "result.md"
