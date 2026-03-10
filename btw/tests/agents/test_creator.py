import pytest

from btw.agents.creator import CreatorAgent


def test_creator_analyze_content_type():
    creator = CreatorAgent(config={})

    assert creator._analyze_content_type("The equation is y = mx + b.") == "formula"
    assert creator._analyze_content_type("This chart shows data and statistics.") == "chart"
    assert creator._analyze_content_type("```js\nconsole.log('hi')\n```") == "code"
    assert creator._analyze_content_type("Once upon a time there was a reader.") == "narrative"


@pytest.mark.asyncio
async def test_creator_process_generates_component_code():
    creator = CreatorAgent(config={})

    result = await creator.process(
        {
            "book_id": "book-001",
            "chapter_index": 2,
            "content": "Supply and demand can be visualized with a chart.",
        }
    )

    assert result["book_id"] == "book-001"
    assert result["chapter_index"] == 2
    assert result["component_type"] == "chart"
    assert "export default function" in result["jsx_code"]
    assert "react" in result["dependencies"]
