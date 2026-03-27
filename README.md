# DeepDoc - Advanced Document Processing System

DeepDoc is a comprehensive document processing system that leverages artificial intelligence to extract, analyze, and understand content from various document formats.

## Project Structure

This repository contains two main implementations:

### 1. Flask Web Application (`flask-deepdoc/`)
A complete web-based document processing system with user interface.

```
flask-deepdoc/
├── app.py                    # Main Flask application
├── document_processor.py      # Core document processing logic
├── requirements.txt          # Python dependencies
├── templates/               # HTML templates
├── static/                 # CSS, JavaScript, images
└── uploads/               # Processed document storage
```

### 2. FastAPI Backend System (`backend/`)
An advanced AI-powered system with vector database and search capabilities.

```
backend/
├── main.py                 # FastAPI application
├── embedding_service.py    # Text embedding services
├── vector_storage.py       # Vector database operations
├── hybrid_search.py        # Hybrid search capabilities
└── requirements.txt       # Dependencies
```

## Quick Start

### Flask Web Application (Simple & Ready to Use)

1. Navigate to the Flask directory:
   ```bash
   cd flask-deepdoc
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Open `http://localhost:5000` in your browser

### FastAPI Backend (Advanced AI System)

1. Start Qdrant vector database:
   ```bash
   cd docker
   docker-compose up -d qdrant
   ```

2. Navigate to the backend directory:
   ```bash
   cd backend
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the API:
   ```bash
   python main.py
   ```

5. Access API docs at `http://localhost:8000/docs`

## Features

### Flask Application
- Multi-format document processing (PDF, DOCX, TXT, XLSX, PPTX, CSV, Images)
- Web-based user interface
- Text extraction and analysis
- Metadata processing
- File management system
- RESTful API endpoints

### FastAPI Backend
- Advanced AI-powered document analysis
- Vector search capabilities
- Hybrid retrieval (keyword + semantic)
- Knowledge base management
- GPU acceleration support
- Embedding models integration

## Supported File Formats

| Format | Extension | Flask | FastAPI | Features |
|--------|-----------|-------|---------|----------|
| PDF | .pdf | ✅ | ✅ | Text extraction, metadata |
| Word | .docx | ✅ | ✅ | Text extraction, metadata |
| Text | .txt | ✅ | ✅ | Direct processing |
| Excel | .xlsx | ✅ | ✅ | Data extraction |
| PowerPoint | .pptx | ✅ | ✅ | Text extraction |
| CSV | .csv | ✅ | ✅ | Data processing |
| Images | .jpg, .png, .gif | ✅ | ✅ | OCR support |

## Dependencies

### Flask Application
- Flask 2.3.3
- PyPDF2
- python-docx
- Werkzeug
- Pillow
- pandas

### FastAPI Backend
- FastAPI
- Qdrant-client
- transformers
- torch
- sentence-transformers
- deepdoctection

## API Endpoints

### Flask Application
- `GET /` - Home page
- `POST /upload` - Upload and process documents
- `GET /documents` - List processed documents
- `POST /api/process` - API endpoint for processing
- `POST /analyze` - Analyze text content

### FastAPI Backend
- `POST /api/v1/documents/upload` - Upload documents
- `POST /api/v1/search` - Search documents
- `GET /api/v1/documents` - List documents
- `POST /api/v1/qa` - Question answering

## Development

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd deepdoc-project
   ```

2. Choose your implementation:
   - For web interface: `cd flask-deepdoc`
   - For advanced AI: `cd backend`

3. Create virtual environment:
   ```bash
   python -m venv venv
   
   # Windows:
   venv\Scripts\activate
   
   # Linux/Mac:
   source venv/bin/activate
   ```

4. Install dependencies and run as described above

## Configuration

### Flask Application
Modify `app.py` to adjust:
- File size limits
- Supported formats
- Upload directory
- Security settings

### FastAPI Backend
Configure via environment variables or `.env` file:
- Qdrant connection settings
- Embedding model selection
- GPU configuration
- API keys for external services

## Security Considerations

- Local processing ensures document privacy
- File type validation prevents malicious uploads
- Secure filename handling
- Resource usage limits
- No external API dependencies for core functionality

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review documentation
3. Submit an issue with detailed information

## Roadmap

- [ ] Advanced OCR integration
- [ ] Machine learning classification
- [ ] Batch processing
- [ ] Cloud storage integration
- [ ] Advanced search features
- [ ] Document comparison
- [ ] Multi-language support
- [ ] Mobile applications

## Acknowledgments

- Flask and FastAPI frameworks
- PyPDF2 and python-docx libraries
- Bootstrap for UI components
- Qdrant vector database
- Hugging Face transformers
- DeepDoctection framework