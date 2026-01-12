# Globals/Initialization
# - Load an embedding model: SentenceTransformer("all-MiniLM-L6-v2") [web:21

# Function: clean_text(s) -> cleaned_string
# - Replace all whitespace runs (spaces/newlines/tabs) with a single space
# - Trim leading/trailing spaces
# - Return cleaned string

# Function: chunk_text(text, chunk_size=900, overlap=150) -> list_of_chunks
# - chunks = empty list
# - i = 0
# - While i < length(text):
#   - chunk = substring(text, from=i, to=i + chunk_size)
#   - Append chunk to chunks
#   - i = i + (chunk_size - overlap)   # slide forward with overlap
# - Return chunks

# Function: heuristic_sensitive(text) -> boolean
# - keywords = ["password", "secret", "api key", "confidential", "ssn"]
# - t = lowercase(text)
# - If any keyword appears in t:
#   - Return True
# - Else:
#   - Return False

# Function: extract_pdf(file_bytes) -> text
# - Create PdfReader from an in-memory bytes buffer
# - pages_text = empty list
# - For each page in reader.pages:
#   - page_text = page.extract_text()
#   - If page_text is null, use empty string
#   - Append page_text to pages_text
# - Return pages_text joined with newline characters

# Function: extract_url(url) -> text
# - html = HTTP GET url (timeout=20 seconds).text
# - readable_doc = ReadabilityDocument(html)
# - main_html = readable_doc.summary(html_partial=True)
# - soup = BeautifulSoup(main_html, "html.parser")
# - text = soup.get_text(separator="\n")
# - Return text