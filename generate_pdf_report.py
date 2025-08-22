#!/usr/bin/env python3
"""
PDF Report Generator
Creates professional PDF reports from contract analysis
"""

import json
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from datetime import datetime

def create_pdf_styles():
    """Create custom styles for the PDF"""
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=20,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#374151'),
        spaceBefore=20,
        spaceAfter=10,
        borderPadding=5
    ))
    
    styles.add(ParagraphStyle(
        name='SubHeader',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#1F2937'),
        spaceBefore=15,
        spaceAfter=5
    ))
    
    styles.add(ParagraphStyle(
        name='RiskHigh',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#DC2626'),
        spaceBefore=5,
        spaceAfter=5,
        leftIndent=20
    ))
    
    styles.add(ParagraphStyle(
        name='RiskMedium',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#D97706'),
        spaceBefore=5,
        spaceAfter=5,
        leftIndent=20
    ))
    
    styles.add(ParagraphStyle(
        name='RiskLow',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#059669'),
        spaceBefore=5,
        spaceAfter=5,
        leftIndent=20
    ))
    
    styles.add(ParagraphStyle(
        name='EntityTag',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6366F1'),
        backColor=colors.HexColor('#EEF2FF'),
        borderColor=colors.HexColor('#C7D2FE'),
        borderWidth=1,
        borderPadding=3
    ))
    
    return styles

def generate_pdf_report():
    """Generate a comprehensive PDF report"""
    
    # Load all available data
    try:
        # Analysis data
        with open('documents/summary_and_risks.json', 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        # Clauses with entities
        clauses_file = 'documents/clauses_with_entities.json'
        clauses = []
        if os.path.exists(clauses_file):
            with open(clauses_file, 'r', encoding='utf-8') as f:
                clauses = json.load(f)
                
    except Exception as e:
        print(f"Error loading data: {e}")
        return None
    
    # Create PDF
    output_file = Path("documents/contract_analysis_report.pdf")
    doc = SimpleDocTemplate(str(output_file), pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = create_pdf_styles()
    story = []
    
    # Title
    story.append(Paragraph("Contract Analysis Report", styles['CustomTitle']))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                          styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    exec_summary = analysis.get("executive_summary", [])
    if isinstance(exec_summary, list):
        for item in exec_summary:
            story.append(Paragraph(f"• {item}", styles['Normal']))
    else:
        story.append(Paragraph(str(exec_summary), styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Key Terms
    story.append(Paragraph("Key Terms", styles['SectionHeader']))
    key_terms = analysis.get("key_terms", {})
    if isinstance(key_terms, dict):
        key_terms_data = [
            ["Attribute", "Value"],
            ["Parties", ', '.join(key_terms.get('parties', ['Not specified']))],
            ["Effective Date", key_terms.get('effective_date', 'Not specified')],
            ["Term", key_terms.get('term', 'Not specified')],
            ["Governing Law", key_terms.get('governing_law', 'Not specified')],
            ["Payment Terms", key_terms.get('payment_terms', 'Not specified')]
        ]
        
        # Add other notable terms
        if key_terms.get("other_notable"):
            for item in key_terms["other_notable"]:
                key_terms_data.append(["Notable", item])
        
        table = Table(key_terms_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(table)
    story.append(Spacer(1, 15))
    
    # Risk Analysis
    story.append(Paragraph("Risk Analysis", styles['SectionHeader']))
    risks = analysis.get("risks", [])
    if risks:
        for risk in risks:
            severity = risk.get("severity", "medium").lower()
            title = risk.get("title", risk.get("clause_title", "General Risk"))
            
            # Risk header with severity color
            risk_style = styles['Normal']
            if severity == 'high':
                risk_style = styles['RiskHigh']
            elif severity == 'medium':
                risk_style = styles['RiskMedium']
            elif severity == 'low':
                risk_style = styles['RiskLow']
            
            story.append(Paragraph(f"<b>[{severity.upper()}] {title}</b>", risk_style))
            
            if risk.get("rationale"):
                story.append(Paragraph(f"<b>Risk:</b> {risk['rationale']}", styles['Normal']))
            
            if risk.get("snippet"):
                story.append(Paragraph(f"<b>Text Snippet:</b> \"{risk['snippet']}\"", styles['Normal']))
            
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No significant risks identified.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Contract Clauses & Entities
    story.append(Paragraph("Contract Clauses & Extracted Entities", styles['SectionHeader']))
    if clauses:
        for i, clause in enumerate(clauses, 1):
            story.append(Paragraph(f"{i}. {clause.get('clause_title', 'Untitled Clause')}", 
                                 styles['SubHeader']))
            
            # Clause text (truncated for readability)
            clause_text = clause.get('clause_text', 'No text available')
            if len(clause_text) > 400:
                clause_text = clause_text[:400] + "..."
            story.append(Paragraph(f"<b>Text:</b> {clause_text}", styles['Normal']))
            
            # Entities
            entities = clause.get('entities', [])
            if entities:
                story.append(Paragraph("<b>Extracted Entities:</b>", styles['Normal']))
                entity_groups = {}
                for entity in entities:
                    label = entity.get('label', entity.get('entity_type', 'OTHER'))
                    text = entity.get('text', '')
                    if label not in entity_groups:
                        entity_groups[label] = []
                    if text not in entity_groups[label]:
                        entity_groups[label].append(text)
                
                for label, texts in entity_groups.items():
                    story.append(Paragraph(f"• <b>{label}:</b> {', '.join(texts)}", styles['Normal']))
            
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No clause data available.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Recommendations
    story.append(Paragraph("Recommendations", styles['SectionHeader']))
    recommendations = analysis.get("recommendations", [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", styles['Normal']))
    else:
        story.append(Paragraph("No specific recommendations at this time.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Open Questions
    story.append(Paragraph("Open Questions", styles['SectionHeader']))
    questions = analysis.get("open_questions", [])
    if questions:
        for i, question in enumerate(questions, 1):
            story.append(Paragraph(f"{i}. {question}", styles['Normal']))
    else:
        story.append(Paragraph("No open questions identified.", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Paragraph("_" * 80, styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>This report was generated using AI-powered contract analysis.</i>", 
                          styles['Normal']))
    story.append(Paragraph("<i>Please review with legal counsel for important decisions.</i>", 
                          styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"PDF report saved to: {output_file}")
    return str(output_file)

if __name__ == "__main__":
    generate_pdf_report()
