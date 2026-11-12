import pytest

from supportpilot.chunker import chunk_text, extract_text


def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_single_chunk():
    assert chunk_text("Hello world.") == ["Hello world."]


def test_chunks_respect_max_chars():
    text = "\n\n".join(f"Paragraph number {i} with some words in it." for i in range(40))
    chunks = chunk_text(text, max_chars=200, overlap=20)
    assert len(chunks) > 3
    assert all(len(c) <= 200 for c in chunks)


def test_long_sentence_is_hard_split():
    chunks = chunk_text("x" * 1000, max_chars=300, overlap=0)
    assert len(chunks) >= 4
    assert all(len(c) <= 300 for c in chunks)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        chunk_text("hello", max_chars=0)
    with pytest.raises(ValueError):
        chunk_text("hello", max_chars=100, overlap=100)


def test_html_extraction_strips_tags_scripts_and_styles():
    html = ("<html><head><style>p{color:red}</style></head><body>"
            "<h1>Title</h1><p>Hello <b>bold</b> world.</p>"
            "<script>alert('x')</script></body></html>")
    text = extract_text(html, ".html")
    assert "Hello bold world." in text
    assert "alert" not in text
    assert "color:red" not in text
    assert "<p>" not in text


def test_markdown_extraction_keeps_words_drops_syntax():
    md = "# Heading\n\nSome **bold** text and a [link](https://example.com/page)."
    text = extract_text(md, ".md")
    assert "Heading" in text
    assert "bold text" in text
    assert "link" in text
    assert "https://example.com" not in text
    assert "**" not in text
