from src.main import extract_keyword_number

SAMPLE_HTML = "<html><body><div>Availability no: 1</div></body></html>"

def test_extract_keyword_number():
    assert extract_keyword_number(SAMPLE_HTML, "Availability no") == 1
