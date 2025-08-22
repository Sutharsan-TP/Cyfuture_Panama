#!/usr/bin/env python3
"""
Flask web server for Dynamite Legal AI frontend
Serves the web interface and provides API endpoints for contract processing
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'dev-key-change-in-production'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('Documents', exist_ok=True)
os.makedirs('documents', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and trigger processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not supported. Please upload PNG, JPG, or PDF files.'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"File uploaded: {filepath}")
        return jsonify({
            'success': True,
            'filename': filename,
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def process_contract():
    """Process the uploaded contract through the AI pipeline"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Copy file to Documents folder for processing
        doc_filepath = os.path.join('Documents', filename)
        import shutil
        shutil.copy2(filepath, doc_filepath)
        
        # Run the pipeline
        logger.info(f"Starting pipeline for: {doc_filepath}")
        result = subprocess.run([
            'python', 'run_all.py', '--file', doc_filepath
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode != 0:
            logger.error(f"Pipeline failed: {result.stderr}")
            return jsonify({
                'error': 'Processing failed',
                'details': result.stderr
            }), 500
        
        # Check for output files
        basename = Path(filename).stem
        results = {}
        
        # Load segmented clauses
        clauses_file = 'documents/segmented_clauses.json'
        if os.path.exists(clauses_file):
            with open(clauses_file, 'r', encoding='utf-8') as f:
                results['clauses'] = json.load(f)
        
        # Load NER results
        ner_file = 'documents/clauses_with_entities.json'
        if os.path.exists(ner_file):
            with open(ner_file, 'r', encoding='utf-8') as f:
                results['entities'] = json.load(f)
        
        # Load analysis results
        analysis_file = 'documents/summary_and_risks.json'
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                results['analysis'] = json.load(f)
        
        # Load markdown report
        md_file = 'documents/summary_and_risks.md'
        if os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                results['report'] = f.read()
        
        logger.info("Pipeline completed successfully")
        return jsonify({
            'success': True,
            'results': results,
            'message': 'Contract processed successfully'
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Processing timeout - please try a smaller file'}), 500
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download processed files"""
    return send_from_directory('documents', filename)

@app.route('/api/generate-comprehensive-report')
def generate_comprehensive_report():
    """Generate comprehensive markdown report with all data"""
    try:
        # Import and run the comprehensive report generator
        import generate_report
        report_path = generate_report.save_comprehensive_report()
        
        if report_path:
            return jsonify({
                'success': True,
                'file': 'comprehensive_report.md',
                'message': 'Comprehensive report generated successfully'
            })
        else:
            return jsonify({'error': 'Failed to generate comprehensive report'}), 500
    except Exception as e:
        logger.error(f"Comprehensive report generation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-pdf-report')
def generate_pdf_report():
    """Generate PDF report"""
    try:
        # Import and run the PDF report generator
        import generate_pdf_report
        pdf_path = generate_pdf_report.generate_pdf_report()
        
        if pdf_path:
            return jsonify({
                'success': True,
                'file': 'contract_analysis_report.pdf',
                'message': 'PDF report generated successfully'
            })
        else:
            return jsonify({'error': 'Failed to generate PDF report'}), 500
    except Exception as e:
        logger.error(f"PDF report generation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Dynamite Legal AI'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
