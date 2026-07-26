import os
import re
import glob

from langsmith import traceable

_HERE = os.path.dirname(os.path.abspath(__file__))

class ParentChildBM25Retriever:
    """
    A lightweight, zero-dependency Parent-Child retriever.
    Splits markdown documents into Parent sections (headers) and Child chunks (paragraphs).
    Indexes children using a clean, vectorized-equivalent TF-IDF/BM25 scoring approach.
    Now maps child matches to the entire document text instead of just the parent section.
    """
    def __init__(self):
        self.documents = [] # List of entire document contents
        self.parents = [] # List of (parent_text, document_index) tuples
        self.children = [] # List of (child_text, parent_index) tuples
        self.vocab = set()
        self.idf = {}
        self.child_words_count = []
        self.child_tf = []

    def add_document(self, text: str):
        """
        Parses a markdown document into parent headers and child paragraphs, storing the full document content.
        """
        doc_idx = len(self.documents)
        self.documents.append(text)
        
        # Split by headers: #, ##, ###
        sections = re.split(r'\n(?=#+ )', text)
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            parent_idx = len(self.parents)
            self.parents.append((section, doc_idx))
            
            # Split section into child chunks (paragraphs/sentences)
            paragraphs = section.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if len(para) > 10:  # Skip trivial short lines
                    self.children.append((para, parent_idx))

    def fit(self):
        """
        Builds the TF-IDF index for the child chunks.
        """
        import math
        self.vocab = set()
        doc_counts = {}
        
        # Preprocess child texts
        processed_docs = []
        for child_text, _ in self.children:
            words = self._tokenize(child_text)
            processed_docs.append(words)
            self.vocab.update(words)
            for w in set(words):
                doc_counts[w] = doc_counts.get(w, 0) + 1
        
        num_docs = len(self.children)
        self.idf = {}
        for w in self.vocab:
            # Standard BM25 IDF
            self.idf[w] = math.log((num_docs - doc_counts[w] + 0.5) / (doc_counts[w] + 0.5) + 1.0)
            
        self.child_tf = []
        self.child_words_count = []
        for words in processed_docs:
            self.child_words_count.append(len(words))
            tf = {}
            for w in words:
                tf[w] = tf.get(w, 0) + 1
            self.child_tf.append(tf)

    def _tokenize(self, text: str) -> list:
        # Convert to lowercase and split alphanumeric words
        return re.findall(r'[a-z0-9]+', text.lower())

    def retrieve(self, query: str, top_k: int = 1) -> str:
        """
        Searches child chunks and returns the entire document text of the best match.
        """
        if not self.children:
            return ""
            
        query_words = self._tokenize(query)
        if not query_words:
            return ""
            
        avg_doc_len = sum(self.child_words_count) / len(self.child_words_count) if self.child_words_count else 1
        k1 = 1.5
        b = 0.75
        
        scores = []
        for idx in range(len(self.children)):
            score = 0.0
            tf = self.child_tf[idx]
            doc_len = self.child_words_count[idx]
            
            for word in query_words:
                if word in tf:
                    # BM25 scoring formula
                    word_tf = tf[word]
                    num = word_tf * (k1 + 1)
                    denom = word_tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
                    score += self.idf.get(word, 0.0) * (num / denom)
            scores.append(score)
            
        if not scores or max(scores) == 0.0:
            return ""
            
        best_idx = scores.index(max(scores))
        _, parent_idx = self.children[best_idx]
        _, doc_idx = self.parents[parent_idx]
        return self.documents[doc_idx]


class DocumentAndPromptLoader:
    """
    Utility loader to load prompt text files and index RAG documents.
    """
    def __init__(self, docs_dir=None, prompts_dir=None):
        self.docs_dir = docs_dir or os.path.join(_HERE, "docs")
        self.prompts_dir = prompts_dir or os.path.join(_HERE, "prompts")
        self.retriever = ParentChildBM25Retriever()
        self.prompts = {}
        
        # Parse and index documents
        self.index_documents()

    def index_documents(self):
        """
        Indexes all markdown files in the docs directory.
        """
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)
            
        md_files = glob.glob(os.path.join(self.docs_dir, "*.md"))
        for filepath in md_files:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Clean out YAML frontmatter if present
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2]
            self.retriever.add_document(content)
        
        self.retriever.fit()

    def load_prompt(self, filename: str) -> str:
        """
        Loads the system prompt from the prompts directory.
        """
        path = os.path.join(self.prompts_dir, filename)
        if not os.path.exists(path):
            # Fallback path lookup
            path = os.path.join(_HERE, "prompts", filename)
            
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt file not found: {filename}")
            
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    @traceable(run_type="retriever", name="ParentChildBM25Retriever")
    def retrieve_context(self, query: str) -> str:
        """
        Retrieves the parent markdown section for the query.
        """
        return self.retriever.retrieve(query)

