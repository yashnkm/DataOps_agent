import os
import tempfile
from typing import List, Dict, Any
from pathlib import Path

import pypdf
import pandas as pd
from docx import Document
import pdfplumber
# Removed unstructured - too heavy for POC deployment


class DocumentProcessor:
    def __init__(self):
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.xlsx': self._process_excel,
            '.xls': self._process_excel,
            '.csv': self._process_csv,
            '.txt': self._process_text
        }
    
    def process_uploaded_files(self, files: List[Any]) -> Dict[str, Any]:
        """Process multiple uploaded files and extract text content"""
        results = {
            'documents': [],
            'total_chunks': 0,
            'processed_files': 0,
            'errors': []
        }
        
        for file in files:
            try:
                # Handle Gradio file object - file is already a path string
                if isinstance(file, str):
                    # File is already saved, use the path directly
                    file_path = file
                    filename = os.path.basename(file_path)
                else:
                    # Handle file object (fallback)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp_file:
                        if hasattr(file, 'read'):
                            tmp_file.write(file.read())
                        else:
                            # File might be bytes or path
                            with open(file, 'rb') as f:
                                tmp_file.write(f.read())
                        file_path = tmp_file.name
                        filename = file.name
                
                # Process the file
                content = self._extract_text_from_file(file_path, filename)
                chunks = self._chunk_text(content, filename)
                
                results['documents'].append({
                    'filename': filename,
                    'content': content,
                    'chunks': chunks,
                    'chunk_count': len(chunks)
                })
                
                results['total_chunks'] += len(chunks)
                results['processed_files'] += 1
                
                # Clean up temp file (only if we created one)
                if not isinstance(file, str) and 'tmp_file' in locals():
                    os.unlink(file_path)
                
            except Exception as e:
                results['errors'].append(f"Error processing {filename if 'filename' in locals() else 'file'}: {str(e)}")
        
        return results
    
    def _extract_text_from_file(self, file_path: str, filename: str) -> str:
        """Extract text from a file based on its extension"""
        file_ext = Path(filename).suffix.lower()
        
        if file_ext in self.supported_formats:
            return self.supported_formats[file_ext](file_path)
        else:
            # Fallback to unstructured library
            return self._process_with_unstructured(file_path)
    
    def _process_pdf(self, file_path: str) -> str:
        """Extract text from PDF using pdfplumber for better table handling"""
        text_content = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Extract text
                text = page.extract_text()
                if text:
                    text_content.append(text)
                
                # Extract tables
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        # Convert table to text representation
                        for row in table:
                            if row:
                                text_content.append('\t'.join(str(cell) for cell in row if cell))
        
        return '\n\n'.join(text_content)
    
    def _process_docx(self, file_path: str) -> str:
        """Extract text from Word documents"""
        doc = Document(file_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)
        
        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text.strip())
                paragraphs.append('\t'.join(row_data))
        
        return '\n\n'.join(paragraphs)
    
    def _process_excel(self, file_path: str) -> str:
        """Extract text from Excel files"""
        excel_file = pd.ExcelFile(file_path)
        all_sheets_text = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Convert dataframe to text representation
            sheet_text = f"Sheet: {sheet_name}\n"
            sheet_text += df.to_string(index=False)
            all_sheets_text.append(sheet_text)
        
        return '\n\n'.join(all_sheets_text)
    
    def _process_csv(self, file_path: str) -> str:
        """Extract text from CSV files"""
        df = pd.read_csv(file_path)
        return df.to_string(index=False)
    
    def _process_text(self, file_path: str) -> str:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _process_with_unstructured(self, file_path: str) -> str:
        """Fallback for unsupported file types"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "Unsupported file format. Supported: PDF, DOCX, XLSX, CSV, TXT"
    
    def _chunk_text(self, text: str, filename: str, chunk_size: int = 1500, overlap: int = 200) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks for better retrieval"""
        if not text or not text.strip():
            return []
        
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            chunk_info = {
                'text': chunk_text,
                'source_file': filename,
                'chunk_index': len(chunks),
                'word_count': len(chunk_words)
            }
            
            chunks.append(chunk_info)
            
            if i + chunk_size >= len(words):
                break
        
        return chunks