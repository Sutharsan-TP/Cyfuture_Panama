// Dynamite Legal AI Frontend JavaScript
class ContractProcessor {
    constructor() {
        this.currentFile = null;
        this.currentFilename = null;
        this.initializeEventListeners();
        this.processingSteps = [
            { id: 'step1', name: 'OCR Extraction', progress: 25 },
            { id: 'step2', name: 'Clause Segmentation', progress: 50 },
            { id: 'step3', name: 'Entity Recognition', progress: 75 },
            { id: 'step4', name: 'Risk Analysis', progress: 100 }
        ];
    }

    initializeEventListeners() {
        // File input handling
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const uploadBtn = document.querySelector('.upload-btn');
        const processBtn = document.getElementById('processBtn');

        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Click to upload (upload area and button)
        uploadArea.addEventListener('click', (e) => {
            // Prevent double triggering if clicking the button
            if (e.target.closest('.upload-btn')) return;
            fileInput.click();
        });
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        
        // Process button
        processBtn.addEventListener('click', () => this.processContract());
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.validateAndDisplayFile(file);
        }
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.currentTarget.classList.remove('dragover');
    }

    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('dragover');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            this.validateAndDisplayFile(files[0]);
        }
    }

    validateAndDisplayFile(file) {
        // Validate file type
        const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
        if (!allowedTypes.includes(file.type)) {
            this.showToast('Please upload a PDF, PNG, or JPG file.', 'error');
            return;
        }

        // Validate file size (50MB max)
        const maxSize = 50 * 1024 * 1024;
        if (file.size > maxSize) {
            this.showToast('File size must be less than 50MB.', 'error');
            return;
        }

        this.currentFile = file;
        this.displayFileInfo(file);
    }

    displayFileInfo(file) {
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const fileInfo = document.getElementById('fileInfo');
        const uploadArea = document.getElementById('uploadArea');

        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
        
        uploadArea.style.display = 'none';
        fileInfo.style.display = 'flex';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async processContract() {
        if (!this.currentFile) {
            this.showToast('Please select a file first.', 'error');
            return;
        }

        try {
            // Upload file first
            await this.uploadFile();
            
            // Show processing section
            this.showProcessingSection();
            
            // Start processing
            await this.startProcessing();
            
        } catch (error) {
            console.error('Processing error:', error);
            this.showError(error.message || 'An unexpected error occurred.');
        }
    }

    async uploadFile() {
        const formData = new FormData();
        formData.append('file', this.currentFile);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Upload failed');
        }

        this.currentFilename = result.filename;
        this.showToast('File uploaded successfully!', 'success');
    }

    showProcessingSection() {
        document.getElementById('uploadSection').style.display = 'none';
        document.getElementById('processingSection').style.display = 'block';
        
        // Reset all steps
        this.processingSteps.forEach(step => {
            const stepElement = document.getElementById(step.id);
            stepElement.classList.remove('active', 'completed');
        });
        
        // Start progress animation
        this.animateProgress();
    }

    async animateProgress() {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        for (let i = 0; i < this.processingSteps.length; i++) {
            const step = this.processingSteps[i];
            const stepElement = document.getElementById(step.id);
            
            // Mark current step as active
            stepElement.classList.add('active');
            progressText.textContent = `${step.name}...`;
            
            // Animate progress bar
            progressFill.style.width = `${step.progress}%`;
            
            // Wait for step to complete (simulated delay)
            await this.delay(2000);
            
            // Mark step as completed
            stepElement.classList.remove('active');
            stepElement.classList.add('completed');
        }
        
        progressText.textContent = 'Processing complete!';
    }

    async startProcessing() {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: this.currentFilename
            })
        });

        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Processing failed');
        }

        // Show results
        this.showResults(result.results);
    }

    showResults(results) {
        document.getElementById('processingSection').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'block';

        // Populate results
        this.populateExecutiveSummary(results.analysis?.executive_summary || 'No summary available.');
        this.populateKeyTerms(results.analysis?.key_terms || []);
        this.populateRisks(results.analysis?.risks || []);
        this.populateClauses(results.entities || []);
        this.populateRecommendations(results.analysis?.recommendations || []);
        this.populateQuestions(results.analysis?.open_questions || []);
        
        this.showToast('Analysis completed successfully!', 'success');
    }

    populateExecutiveSummary(summary) {
        const container = document.getElementById('summaryContent');
        
        // Handle both string and array formats
        if (Array.isArray(summary)) {
            container.innerHTML = summary.map(item => `<p>${this.escapeHtml(item)}</p>`).join('');
        } else {
            container.innerHTML = `<p>${this.escapeHtml(summary)}</p>`;
        }
    }

    populateKeyTerms(terms) {
        const container = document.getElementById('termsList');
        
        // Handle both array and object formats
        let termArray = [];
        if (Array.isArray(terms)) {
            termArray = terms;
        } else if (terms && typeof terms === 'object') {
            // Extract terms from nested object structure
            if (terms.parties) termArray.push(...terms.parties);
            if (terms.payment_terms) termArray.push(terms.payment_terms);
            if (terms.other_notable) termArray.push(...terms.other_notable);
            // Add other fields if they exist
            Object.keys(terms).forEach(key => {
                if (key !== 'parties' && key !== 'payment_terms' && key !== 'other_notable' && terms[key]) {
                    if (typeof terms[key] === 'string') {
                        termArray.push(terms[key]);
                    }
                }
            });
        }
        
        if (termArray.length === 0) {
            container.innerHTML = '<p>No key terms identified.</p>';
            return;
        }
        
        container.innerHTML = termArray.map(term => 
            `<span class="term-tag">${this.escapeHtml(term)}</span>`
        ).join('');
    }

    populateRisks(risks) {
        const container = document.getElementById('risksContainer');
        
        if (risks.length === 0) {
            container.innerHTML = '<p>No significant risks identified.</p>';
            return;
        }
        
        container.innerHTML = risks.map(risk => `
            <div class="risk-item ${(risk.severity || 'medium').toLowerCase()}">
                <div class="risk-header">
                    <span class="risk-title">${this.escapeHtml(risk.title || risk.clause_title || 'General Risk')}</span>
                    <span class="risk-severity ${(risk.severity || 'medium').toLowerCase()}">
                        ${risk.severity || 'Medium'}
                    </span>
                </div>
                <div class="risk-rationale">
                    ${this.escapeHtml(risk.rationale || 'No details provided.')}
                </div>
                ${risk.snippet ? `<div class="risk-snippet"><em>"${this.escapeHtml(risk.snippet)}"</em></div>` : ''}
            </div>
        `).join('');
    }

    populateClauses(clausesWithEntities) {
        const container = document.getElementById('clausesContainer');
        
        if (clausesWithEntities.length === 0) {
            container.innerHTML = '<p>No clauses available.</p>';
            return;
        }
        
        container.innerHTML = clausesWithEntities.map(clause => `
            <div class="clause-item">
                <div class="clause-title">${this.escapeHtml(clause.clause_title || 'Untitled Clause')}</div>
                <div class="clause-text">${this.escapeHtml(clause.clause_text?.substring(0, 200) || 'No text available.')}${clause.clause_text?.length > 200 ? '...' : ''}</div>
                <div class="entities-container">
                    ${(clause.entities || []).map(entity => 
                        `<span class="entity-tag ${entity.label}">${this.escapeHtml(entity.text)} (${entity.label})</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');
    }

    populateRecommendations(recommendations) {
        const container = document.getElementById('recommendationsList');
        
        if (recommendations.length === 0) {
            container.innerHTML = '<li>No specific recommendations at this time.</li>';
            return;
        }
        
        container.innerHTML = recommendations.map(rec => 
            `<li>${this.escapeHtml(rec)}</li>`
        ).join('');
    }

    populateQuestions(questions) {
        const container = document.getElementById('questionsList');
        
        if (questions.length === 0) {
            container.innerHTML = '<li>No open questions identified.</li>';
            return;
        }
        
        container.innerHTML = questions.map(question => 
            `<li>${this.escapeHtml(question)}</li>`
        ).join('');
    }

    showError(message) {
        document.getElementById('processingSection').style.display = 'none';
        document.getElementById('errorSection').style.display = 'block';
        document.getElementById('errorMessage').textContent = message;
        this.showToast('Processing failed. Please try again.', 'error');
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Global functions for button handlers
function toggleDownloadMenu() {
    const menu = document.getElementById('downloadMenu');
    menu.classList.toggle('show');
    
    // Close menu when clicking outside
    document.addEventListener('click', function closeMenu(e) {
        if (!e.target.closest('.download-dropdown')) {
            menu.classList.remove('show');
            document.removeEventListener('click', closeMenu);
        }
    });
}

function downloadBasicReport() {
    window.open('/api/download/summary_and_risks.md', '_blank');
    document.getElementById('downloadMenu').classList.remove('show');
}

async function downloadComprehensiveReport() {
    try {
        // Generate comprehensive report
        const response = await fetch('/api/generate-comprehensive-report');
        const result = await response.json();
        
        if (result.success) {
            // Download the generated file
            window.open(`/api/download/${result.file}`, '_blank');
            showToast(result.message, 'success');
        } else {
            showToast('Failed to generate comprehensive report', 'error');
        }
    } catch (error) {
        console.error('Error generating comprehensive report:', error);
        showToast('Error generating comprehensive report', 'error');
    }
    document.getElementById('downloadMenu').classList.remove('show');
}

async function downloadPDFReport() {
    try {
        // Show loading state
        showToast('Generating PDF report...', 'info');
        
        // Generate PDF report
        const response = await fetch('/api/generate-pdf-report');
        const result = await response.json();
        
        if (result.success) {
            // Download the generated file
            window.open(`/api/download/${result.file}`, '_blank');
            showToast(result.message, 'success');
        } else {
            showToast('Failed to generate PDF report', 'error');
        }
    } catch (error) {
        console.error('Error generating PDF report:', error);
        showToast('Error generating PDF report', 'error');
    }
    document.getElementById('downloadMenu').classList.remove('show');
}

// Legacy function for backward compatibility
function downloadReport() {
    downloadBasicReport();
}

function showToast(message, type = 'info') {
    // Create toast if it doesn't exist
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    
    // Set message and type
    toast.textContent = message;
    toast.className = `toast toast-${type} show`;
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function resetApp() {
    // Hide all sections except upload
    document.getElementById('processingSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
    document.getElementById('uploadSection').style.display = 'block';
    
    // Reset upload area
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('fileInput').value = '';
    
    // Reset processor
    if (window.processor) {
        window.processor.currentFile = null;
        window.processor.currentFilename = null;
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.processor = new ContractProcessor();
    console.log('Dynamite Legal AI Frontend initialized');
});
