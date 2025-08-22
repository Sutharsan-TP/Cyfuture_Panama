# Dynamite Legal AI - Web Frontend

## Quick Start

1. **Install Flask dependencies:**
   ```bash
   pip install flask werkzeug
   ```

2. **Start the web server:**
   ```bash
   python app.py
   ```

3. **Open your browser:**
   - Go to: http://localhost:5000
   - Upload a contract (PDF, PNG, JPG)
   - Click "Process Contract"
   - Review the analysis results

## Frontend Features

### 🎨 Modern UI
- Clean, professional design with gradient backgrounds
- Responsive layout that works on desktop and mobile
- Drag & drop file upload with visual feedback
- Real-time processing progress with animated steps

### 📱 User Experience
- **File Upload**: Drag & drop or click to browse
- **File Validation**: Checks file type and size (50MB max)
- **Progress Tracking**: Visual progress bar with step indicators
- **Results Display**: Structured cards showing:
  - Executive Summary
  - Key Terms (as tags)
  - Risk Analysis (color-coded by severity)
  - Contract Clauses with extracted entities
  - Recommendations
  - Open Questions

### 🔧 Technical Stack
- **Backend**: Flask web server
- **Frontend**: Vanilla JavaScript (no frameworks needed)
- **Styling**: Modern CSS with flexbox/grid
- **Icons**: Font Awesome for professional icons
- **API**: RESTful endpoints for upload and processing

## File Structure
```
├── app.py                 # Flask web server
├── templates/
│   └── index.html        # Main application page
├── static/
│   ├── css/
│   │   └── style.css     # Responsive styling
│   └── js/
│       └── app.js        # Frontend logic
├── uploads/              # Temporary file storage
└── documents/            # Processing outputs
```

## API Endpoints

### POST /api/upload
Upload a contract file for processing.
- **Body**: multipart/form-data with 'file' field
- **Response**: `{"success": true, "filename": "..."}`

### POST /api/process
Process an uploaded contract through the AI pipeline.
- **Body**: `{"filename": "uploaded-file.pdf"}`
- **Response**: Processing results with clauses, entities, and analysis

### GET /api/download/<filename>
Download processed files (JSON reports, etc.)

### GET /health
Health check endpoint for monitoring

## Usage Examples

### Basic Upload & Process
1. Drag a PDF contract onto the upload area
2. Click "Process Contract" 
3. Watch the 4-step progress animation:
   - 🔍 OCR Extraction
   - ✂️ Clause Segmentation  
   - 🏷️ Entity Recognition
   - 📊 Risk Analysis
4. Review results in organized cards
5. Download the full report as Markdown

### Error Handling
- Invalid file types show user-friendly messages
- Processing timeouts (5 minutes) are handled gracefully
- Network errors display retry options
- Toast notifications keep users informed

## Customization

### Styling
Edit `static/css/style.css` to customize:
- Color scheme (current: blue gradient)
- Card layouts and spacing
- Typography and icons
- Mobile responsiveness

### Functionality  
Edit `static/js/app.js` to modify:
- File validation rules
- Progress animation timing
- Results display format
- Error handling behavior

### Backend
Edit `app.py` to adjust:
- File size limits
- Processing timeout
- API response format
- Security settings

## Deployment Notes

### Development
- Flask runs in debug mode with auto-reload
- Accessible at http://localhost:5000
- File uploads stored in `uploads/` folder

### Production
- Set `app.run(debug=False)` 
- Use proper WSGI server (gunicorn, uwsgi)
- Configure reverse proxy (nginx)
- Set secure `SECRET_KEY`
- Add HTTPS for file uploads

## Browser Support
- Chrome/Edge: Full support
- Firefox: Full support  
- Safari: Full support
- Mobile browsers: Responsive design

---
**Ready to demo:** Start the server and navigate to http://localhost:5000!
