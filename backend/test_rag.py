"""
RAG Manager Integration Test Script
Tests: ingestion, storage, keyword search, tool binding
"""
import sys
import os
import json

# Ensure we can import from the backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.rag_manager import RagManager

TEST_NODE_ID = "test-rag-node-001"

def test_txt_ingestion():
    print("=" * 60)
    print("TEST 1: TXT Document Ingestion")
    print("=" * 60)

    sample_text = """
    Artificial Intelligence (AI) is a branch of computer science 
    that aims to create intelligent machines. Machine Learning is 
    a subset of AI that enables systems to learn from data.
    Deep Learning uses neural networks with many layers.
    Natural Language Processing (NLP) deals with the interaction
    between computers and human language.
    Reinforcement Learning is a type of ML where an agent learns
    to make decisions by taking actions in an environment.
    """

    file_bytes = sample_text.encode("utf-8")
    result = RagManager.add_file(
        node_id=TEST_NODE_ID,
        filename="ai_overview.txt",
        file_bytes=file_bytes,
        chunk_size=200,
        chunk_overlap=30,
    )

    print(f"  File ID: {result['id']}")
    print(f"  Filename: {result['filename']}")
    print(f"  Size: {result['size']} bytes")
    print(f"  Chunks: {result['chunks_count']}")
    assert result["chunks_count"] > 0, "Expected at least 1 chunk"
    print("  ✅ PASS\n")
    return result


def test_list_files():
    print("=" * 60)
    print("TEST 2: List Files for Node")
    print("=" * 60)

    files = RagManager.list_files(TEST_NODE_ID)
    print(f"  Found {len(files)} file(s)")
    for f in files:
        print(f"    - {f['filename']} ({f['size']} bytes)")
    assert len(files) >= 1, "Expected at least 1 file"
    print("  ✅ PASS\n")
    return files


def test_keyword_search():
    print("=" * 60)
    print("TEST 3: Keyword Fallback Search (TF-IDF)")
    print("=" * 60)

    results = RagManager.search(TEST_NODE_ID, "machine learning subset", top_k=2)
    print(f"  Query: 'machine learning subset'")
    print(f"  Results: {len(results)}")
    for i, r in enumerate(results):
        print(f"    [{i+1}] score={r['score']:.4f}  text={r['text'][:80]}...")
    assert len(results) > 0, "Expected at least 1 result"
    # The top result should contain 'machine' or 'learning'
    assert "machine" in results[0]["text"].lower() or "learning" in results[0]["text"].lower(), \
        "Top result should mention machine or learning"
    print("  ✅ PASS\n")


def test_search_no_results():
    print("=" * 60)
    print("TEST 4: Search with no matching query")
    print("=" * 60)

    results = RagManager.search(TEST_NODE_ID, "xyzzyspoon", top_k=3)
    print(f"  Query: 'xyzzyspoon'")
    print(f"  Results: {len(results)}")
    assert len(results) == 0, "Expected 0 results for gibberish query"
    print("  ✅ PASS\n")


def test_rag_tool_creation():
    print("=" * 60)
    print("TEST 5: LangChain Tool Creation & Invocation")
    print("=" * 60)

    from models.graph import Node, NodeData, Position
    from routers.langgraph_compiler_agentic import AgenticLangGraphCompiler

    rag_node = Node(
        id=TEST_NODE_ID,
        type="rag",
        position=Position(x=0, y=0),
        data=NodeData(
            label="Test KB",
            ragName="AI Overview",
            topK=2,
            ragFiles=[{"id": "fake", "filename": "ai_overview.txt", "size": 100}],
        )
    )

    # We just need an instance to call _create_rag_tool
    from models.graph import GraphSchema
    schema = GraphSchema(nodes=[rag_node], edges=[])
    compiler = AgenticLangGraphCompiler(schema)

    tool = compiler._create_rag_tool(rag_node)
    print(f"  Tool name: {tool.name}")
    print(f"  Tool description: {tool.description}")

    # Invoke the tool
    output = tool.invoke("deep learning neural")
    print(f"  Invocation output (first 120 chars): {output[:120]}...")
    assert len(output) > 0, "Tool should return non-empty output"
    print("  ✅ PASS\n")


def test_delete_file(file_id: str):
    print("=" * 60)
    print("TEST 6: Delete File")
    print("=" * 60)

    success = RagManager.delete_file(TEST_NODE_ID, file_id)
    print(f"  Delete result: {success}")
    assert success, "Delete should return True"

    files = RagManager.list_files(TEST_NODE_ID)
    assert len(files) == 0, f"Expected 0 files after delete, got {len(files)}"
    print("  ✅ PASS\n")


def test_pdf_ingestion():
    print("=" * 60)
    print("TEST 7: PDF Ingestion (pypdf)")
    print("=" * 60)

    try:
        from pypdf import PdfWriter
        import io

        # Create a minimal PDF in-memory
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        # pypdf PdfWriter doesn't directly support writing text in a simple way,
        # so we'll just verify that the pipeline runs without errors on a blank PDF.
        # For a real test you'd supply an actual PDF file.
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        try:
            result = RagManager.add_file(
                node_id=TEST_NODE_ID,
                filename="blank.pdf",
                file_bytes=pdf_bytes,
                chunk_size=200,
                chunk_overlap=30,
            )
            print(f"  Blank PDF indexed: {result['chunks_count']} chunks")
            # Clean up
            RagManager.delete_file(TEST_NODE_ID, result["id"])
        except ValueError as e:
            # Expected: blank PDF has no extractable text
            print(f"  Correctly rejected blank PDF: {e}")

        print("  ✅ PASS\n")

    except ImportError:
        print("  ⚠️ pypdf not installed, skipping PDF test")
        print("  ⚠️ SKIP\n")


if __name__ == "__main__":
    print("\n🔬 RAG Manager Test Suite\n")

    try:
        # Clean up any leftover test data
        for f in RagManager.list_files(TEST_NODE_ID):
            RagManager.delete_file(TEST_NODE_ID, f["id"])

        result = test_txt_ingestion()
        test_list_files()
        test_keyword_search()
        test_search_no_results()
        test_rag_tool_creation()
        test_delete_file(result["id"])
        test_pdf_ingestion()

        print("=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
