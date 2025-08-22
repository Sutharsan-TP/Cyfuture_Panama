# Dynamite Legal AI - Contract Analysis Platform

A comprehensive AI-powered contract analysis platform that provides intelligent document processing, risk assessment, and entity extraction for legal documents.

## 🚀 Features

### Core Functionality
- **Multi-format Support**: Process PDF documents and images (PNG, JPG)
- **OCR Processing**: Advanced text extraction from scanned documents
- **Intelligent Segmentation**: Smart clause identification and separation
- **Named Entity Recognition**: Extract parties, dates, amounts, locations, and legal terms
- **Risk Analysis**: AI-powered risk assessment with severity levels
- **Professional Web Interface**: Modern, responsive UI with real-time progress tracking

### Advanced Capabilities
- **Multiple Download Formats**: Basic report, comprehensive report, and PDF generation
- **Real-time Processing**: Live progress tracking with 4-step pipeline visualization
- **Professional Reports**: Styled PDF reports with color-coded risk levels
- **Entity Visualization**: Interactive tags for extracted entities
- **Comprehensive Analysis**: Executive summaries, key terms, recommendations, and open questions

## 🛠️ Technology Stack

### Backend
- **Python 3.11+**
- **Flask** - Web framework
- **Google Gemini AI** - Document analysis and risk assessment
- **Transformers** - NER model processing
- **ONNX Runtime** - Optimized model inference
- **PyTesseract** - OCR processing
- **PyMuPDF** - PDF text extraction
- **ReportLab** - PDF report generation

### Frontend
- **HTML5/CSS3** - Modern responsive design
- **Vanilla JavaScript** - Interactive UI components
- **Font Awesome** - Professional icons
- **CSS Grid/Flexbox** - Advanced layouts

### AI Models
- **Quantized NER Model** - Optimized entity extraction
- **Google Gemini Pro** - Advanced text analysis
- **Custom Risk Assessment** - Legal-specific risk evaluation

## 📁 Project Structure

```
Cyfora/
├── app.py                          # Flask web application
├── run_all.py                      # Main processing pipeline
├── analysis.py                     # AI-powered analysis engine
├── segmentation.py                 # Clause segmentation
├── ner_extraction_quantized.py     # Named entity recognition
├── generate_report.py              # Comprehensive report generator
├── generate_pdf_report.py          # PDF report generator
├── gemini_ocr.py                   # OCR processing
├── quantize_model.py               # Model optimization
├── requirements.txt                # Python dependencies
├── templates/
│   └── index.html                  # Main web interface
├── static/
│   ├── css/
│   │   └── style.css              # Application styling
│   └── js/
│       └── app.js                 # Frontend logic
└── documents/                      # Generated reports and analysis
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Git
- Google AI API key (for Gemini)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Cyfora
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
Create a `.env` file:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

4. **Download and quantize the NER model**
```bash
python quantize_model.py
```

5. **Start the application**
```bash
python app.py
```

6. **Access the application**
Open your browser and go to: `http://localhost:5000`

## 📊 Usage

### Web Interface
1. **Upload Document**: Drag and drop or click to select PDF/image files
2. **Processing**: Watch real-time progress through 4 pipeline stages
3. **Review Results**: Analyze executive summary, risks, clauses, and entities
4. **Download Reports**: Choose from multiple report formats

### Processing Pipeline
1. **OCR/Text Extraction** - Extract text from documents
2. **Clause Segmentation** - Identify and separate contract sections
3. **Entity Recognition** - Extract legal entities and terms
4. **AI Analysis** - Generate insights, risks, and recommendations

### Report Formats
- **Basic Report** - Simple markdown with key findings
- **Comprehensive Report** - Complete analysis with all extracted data
- **PDF Report** - Professional formatted document with styling

## 🔧 Configuration

### Environment Variables
```bash
GOOGLE_API_KEY=your_gemini_api_key    # Required for AI analysis
UPLOAD_FOLDER=uploads                 # File upload directory
MAX_CONTENT_LENGTH=52428800          # 50MB upload limit
```

### Model Configuration
- NER model is automatically quantized for optimal performance
- Supports CPU and GPU inference
- Configurable batch sizes and inference parameters

## 📈 Performance

- **File Size Limit**: Up to 50MB per document
- **Processing Time**: 30-120 seconds depending on document complexity
- **Supported Formats**: PDF, PNG, JPG
- **Concurrent Processing**: Single document processing with queue support

## 🛡️ Security Features

- File type validation
- Size limit enforcement
- Secure file handling
- Input sanitization
- Error handling and logging

## 🎯 Use Cases

### Legal Professionals
- **Contract Review**: Rapid analysis of legal agreements
- **Risk Assessment**: Identify potential legal risks and issues
- **Due Diligence**: Comprehensive document analysis
- **Compliance Checking**: Ensure regulatory compliance

### Business Applications
- **Vendor Agreements**: Analyze supplier contracts
- **Employment Contracts**: Review hiring agreements
- **Real Estate**: Property purchase and lease agreements
- **Insurance Policies**: Policy term analysis

## 🔄 API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload document for processing
- `POST /api/process` - Start analysis pipeline
- `GET /api/download/<filename>` - Download generated reports

### Report Generation
- `GET /api/generate-comprehensive-report` - Generate complete analysis
- `GET /api/generate-pdf-report` - Create styled PDF report

### Utility
- `GET /health` - Application health check

## 📋 Dependencies

### Core Libraries
```
flask>=2.3.0
werkzeug>=2.3.0
pillow>=10.0.0
pytesseract>=0.3.10
google-generativeai>=0.3.0
python-dotenv>=1.0.0
transformers>=4.30.0
optimum>=1.12.0
onnx>=1.14.0
onnxruntime>=1.15.0
torch>=2.0.0
huggingface_hub>=0.16.0
pymupdf>=1.23.0
reportlab>=4.0.0
weasyprint>=60.0
markdown>=3.5.0
```

## 🚨 Troubleshooting

### Common Issues
1. **OCR Not Working**: Install Tesseract OCR system dependency
2. **Memory Issues**: Reduce batch size in NER processing
3. **API Errors**: Verify Google AI API key configuration
4. **PDF Generation Fails**: Check ReportLab installation

### Error Handling
- Comprehensive logging system
- User-friendly error messages
- Graceful degradation for missing components
- Timeout protection for long-running processes

## 📞 Support

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Review application logs
3. Verify all dependencies are installed
4. Ensure API keys are properly configured

## 🔮 Future Enhancements

- **Multi-language Support**: Process documents in various languages
- **Batch Processing**: Handle multiple documents simultaneously
- **Advanced Analytics**: Detailed statistical analysis
- **Integration APIs**: Connect with legal software systems
- **Cloud Deployment**: Scalable cloud infrastructure
- **User Authentication**: Multi-user support with role management

## 📄 License

This project is developed for educational and professional use. Please ensure compliance with all applicable laws and regulations when processing legal documents.

---

**Built with ❤️ for the legal technology community**
