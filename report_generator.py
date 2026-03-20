"""
Enhanced PDF Report Generator for Clinical Reports
Generates professional, clinical-grade PDF reports with charts and recommendations
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import Frame, PageTemplate
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime
import os
from typing import Dict, List
import io


class ClinicalReportGenerator:
    """Generate professional PDF clinical reports"""
    
    def __init__(self, output_dir: str = "reports"):
        """Initialize report generator"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Define colors
        self.colors = {
            'primary': colors.HexColor('#6366f1'),
            'secondary': colors.HexColor('#ec4899'),
            'success': colors.HexColor('#10b981'),
            'warning': colors.HexColor('#f59e0b'),
            'danger': colors.HexColor('#ef4444'),
            'dark': colors.HexColor('#1a1f3a'),
            'light_gray': colors.HexColor('#f3f4f6')
        }
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.colors['primary'],
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.colors['dark'],
            spaceAfter=12,
            fontName='Helvetica-Bold'
        ))
        
        # Risk alert style
        self.styles.add(ParagraphStyle(
            name='RiskAlert',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=self.colors['danger'],
            borderPadding=10,
            spaceAfter=15
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=TA_JUSTIFY
        ))
    
    def generate_report(self, analysis_data: Dict, assessment: Dict, 
                       recommendations: List[Dict], chart_image_path: str = None, 
                       output_filename: str = None) -> str:
        """
        Generate comprehensive clinical PDF report
        
        Args:
            analysis_data: Analysis results with measurements
            assessment: Clinical assessment from ClinicalRulesEngine
            recommendations: Recommendations from RecommendationGenerator
            chart_image_path: Path to temporary chart image file
            output_filename: Optional custom filename
        
        Returns:
            Path to generated PDF file
        """
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"clinical_report_{timestamp}.pdf"
        
        filepath = os.path.join(self.output_dir, output_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        
        # Header
        story.extend(self._create_header(analysis_data))
        
        # Risk Assessment Summary
        story.extend(self._create_risk_summary(assessment))
        
        # Measurements Table
        story.extend(self._create_measurements_table(analysis_data, assessment))

        # IF chart image is provided, insert it here
        if chart_image_path and os.path.exists(chart_image_path):
            story.extend(self._create_chart_section(chart_image_path))
        
        # Advanced Biometrics (EFW, CI)
        story.extend(self._create_advanced_biometrics_section(assessment))
        
        # Growth Pattern Analysis
        story.extend(self._create_growth_analysis(assessment))
        
        # Clinical Recommendations
        story.extend(self._create_recommendations_section(recommendations))
        
        # Follow-up Plan
        story.extend(self._create_followup_section(assessment))
        
        # System Intelligence & Performance
        story.extend(self._create_performance_section(analysis_data, assessment))
        
        # Footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        return filepath

    def _create_chart_section(self, image_path: str) -> List:
        """Create section for growth chart image"""
        elements = []
        title = Paragraph("Longitudinal Growth Trajectory", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        try:
            img = Image(image_path, width=6*inch, height=3*inch)
            img.hAlign = 'CENTER'
            
            # Add a Border/Frame for the image
            table = Table([[img]], colWidths=[6.2*inch])
            table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, self.colors['primary']),
                ('BACKGROUND', (0,0), (-1,-1), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))
        except Exception as e:
            elements.append(Paragraph(f"<i>[Chart Image Could Not Be Processed: {str(e)}]</i>", self.styles['Normal']))
            
        return elements
    
    def _create_header(self, analysis_data: Dict) -> List:
        """Create report header"""
        elements = []
        
        # Title
        title = Paragraph("CradleMetrics Clinical Report", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Report info table
        report_date = datetime.now().strftime("%B %d, %Y %I:%M %p")
        ga_value = analysis_data.get('GA', {}).get('value', 'N/A')
        
        info_data = [
            ['Report Date:', report_date],
            ['Gestational Age:', f"{ga_value} weeks" if ga_value != 'N/A' else 'N/A'],
            ['Analysis Type:', 'Fetal Biometric Assessment'],
            ['Standards:', 'INTERGROWTH-21st International Standards']
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['dark']),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_risk_summary(self, assessment: Dict) -> List:
        """Create risk assessment summary box"""
        elements = []
        
        risk_level = assessment.get('overall_risk', 'normal')
        risk_colors = {
            'normal': self.colors['success'],
            'borderline': self.colors['warning'],
            'high_risk': self.colors['danger'],
            'critical': colors.HexColor('#dc2626')
        }
        
        risk_labels = {
            'normal': 'NORMAL - No Significant Concerns',
            'borderline': 'BORDERLINE - Monitoring Recommended',
            'high_risk': 'HIGH RISK - Clinical Review Required',
            'critical': 'CRITICAL - Immediate Attention Required'
        }
        
        # Risk level box
        risk_text = f"<b>Overall Risk Assessment: {risk_labels.get(risk_level, 'UNKNOWN')}</b>"
        risk_para = Paragraph(risk_text, self.styles['Normal'])
        
        risk_table = Table([[risk_para]], colWidths=[6.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), risk_colors.get(risk_level, self.colors['light_gray'])),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('PADDING', (0, 0), (-1, -1), 15),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(risk_table)
        
        # Add Anatomical Quality Score
        if 'quality_score' in assessment:
            q = assessment['quality_score']
            q_text = f"<b>Anatomical Quality Score: {q['score']}/100 ({q['status']})</b>"
            q_para = Paragraph(q_text, self.styles['CustomBody'])
            elements.append(Spacer(1, 0.1*inch))
            elements.append(q_para)
            
            # Add criteria bullets
            for criterion in q.get('criteria', []):
                bullet = Paragraph(f"• {criterion}", self.styles['CustomBody'])
                elements.append(bullet)
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_measurements_table(self, analysis_data: Dict, assessment: Dict) -> List:
        """Create measurements table with risk indicators"""
        elements = []
        
        # Section title
        title = Paragraph("Biometric Measurements", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        # Table data
        data = [['Measurement', 'Value', 'Percentile', 'Status', 'Assessment']]
        
        measurements = ['HC', 'AC', 'BPD', 'FL']
        measurement_names = {
            'HC': 'Head Circumference',
            'AC': 'Abdominal Circumference',
            'BPD': 'Biparietal Diameter',
            'FL': 'Femur Length'
        }
        
        for key in measurements:
            if key in analysis_data:
                value = analysis_data[key].get('value', 'N/A')
                percentile = analysis_data[key].get('percentile', 'N/A')
                
                # Get assessment
                assess = assessment.get('measurements', {}).get(key, {})
                status_icon = assess.get('icon', '-')
                risk_level = assess.get('risk_level', 'normal')
                
                # Format values
                value_str = f"{value} mm" if value != 'N/A' else 'N/A'
                percentile_str = f"{percentile}th" if percentile != 'N/A' else 'N/A'
                status_str = f"{status_icon} {risk_level.replace('_', ' ').title()}"
                
                # Format messages as Paragraphs to allow wrapping
                assessment_msg = assess.get('message', 'No data')
                assessment_para = Paragraph(assessment_msg, self.styles['CustomBody'])
                
                data.append([
                    measurement_names[key],
                    value_str,
                    percentile_str,
                    status_str,
                    assessment_para
                ])
        
        # Create table with adjusted column widths to give more space to assessment
        table = Table(data, colWidths=[1.4*inch, 0.8*inch, 0.8*inch, 1.2*inch, 2.3*inch])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (3, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'LEFT'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_advanced_biometrics_section(self, assessment: Dict) -> List:
        """Create section for EFW and Cephalic Index"""
        elements = []
        
        has_efw = 'efw' in assessment
        has_ci = 'ci' in assessment
        
        if not has_efw and not has_ci:
            return elements
            
        # Section title
        title = Paragraph("Advanced Clinical Metrics", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        data = [['Metric', 'Value', 'Unit', 'Percentile/Status', 'Description']]
        
        if has_efw:
            efw = assessment['efw']
            percentile = efw.get('percentile', 'N/A')
            perc_str = f"{percentile}%" if percentile != 'N/A' else 'N/A'
            data.append([
                'Estimated Fetal Weight',
                f"{efw['value']}",
                efw['unit'],
                perc_str,
                efw['description']
            ])
        if has_ci:
            ci = assessment['ci']
            status = ci.get('status', 'N/A').title()
            data.append([
                'Cephalic Index',
                f"{ci['value']}",
                ci['unit'],
                status,
                ci['description']
            ])
            
        if 'afi' in assessment:
            afi = assessment['afi']
            data.append([
                'Amniotic Fluid Index',
                f"{afi['value']}",
                afi['unit'],
                afi['classification'],
                afi['description']
            ])
            
        if 'doppler' in assessment:
            doppler = assessment['doppler']
            data.append([
                'Doppler (CPR)',
                f"{doppler.get('cpr', 'N/A')}",
                '',
                doppler.get('classification', 'N/A'),
                f"UA-PI: {doppler.get('ua_pi', 'N/A')}, MCA-PI: {doppler.get('mca_pi', 'N/A')}"
            ])
            
        table = Table(data, colWidths=[1.8*inch, 0.8*inch, 0.7*inch, 1.2*inch, 2.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.colors['light_gray']]),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _create_growth_analysis(self, assessment: Dict) -> List:
        """Create growth pattern analysis section"""
        elements = []
        
        if 'growth_pattern' not in assessment:
            return elements
        
        # Section title
        title = Paragraph("Growth Pattern Analysis", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        pattern = assessment['growth_pattern'].get('pattern', 'Unknown')
        description = assessment['growth_pattern'].get('description', 'No description available')
        
        text = f"<b>Pattern:</b> {pattern.upper()}<br/><br/>{description}"
        para = Paragraph(text, self.styles['CustomBody'])
        elements.append(para)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_recommendations_section(self, recommendations: List[Dict]) -> List:
        """Create clinical recommendations section"""
        elements = []
        
        # Section title
        title = Paragraph("Clinical Recommendations", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        if not recommendations:
            para = Paragraph("No specific recommendations at this time. Continue routine prenatal care.", 
                           self.styles['CustomBody'])
            elements.append(para)
        else:
            # Group by priority
            high_priority = [r for r in recommendations if r.get('priority') == 'high']
            medium_priority = [r for r in recommendations if r.get('priority') == 'medium']
            low_priority = [r for r in recommendations if r.get('priority') == 'low']
            
            for priority_group, label, color in [
                (high_priority, 'High Priority', self.colors['danger']),
                (medium_priority, 'Medium Priority', self.colors['warning']),
                (low_priority, 'Routine', self.colors['success'])
            ]:
                if priority_group:
                    # Priority header
                    header = Paragraph(f"<b>{label}:</b>", self.styles['CustomBody'])
                    elements.append(header)
                    elements.append(Spacer(1, 0.05*inch))
                    
                    # Recommendations list
                    for rec in priority_group:
                        bullet = Paragraph(f"• {rec['text']}", self.styles['CustomBody'])
                        elements.append(bullet)
                        elements.append(Spacer(1, 0.05*inch))
                    
                    elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _create_followup_section(self, assessment: Dict) -> List:
        """Create follow-up plan section"""
        elements = []
        
        from recommendations import RecommendationGenerator
        rec_gen = RecommendationGenerator()
        follow_up = rec_gen.generate_follow_up_plan(assessment)
        
        # Section title
        title = Paragraph("Follow-up Plan", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        # Follow-up details
        text = f"""
        <b>Next Ultrasound:</b> {follow_up['next_scan']}<br/>
        <b>Frequency:</b> {follow_up['frequency']}<br/>
        <b>Specialist Consultation:</b> {follow_up['specialist']}<br/>
        <b>Additional Tests:</b> {', '.join(follow_up['additional'])}
        """
        para = Paragraph(text, self.styles['CustomBody'])
        elements.append(para)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _create_performance_section(self, analysis_data: Dict, assessment: Dict) -> List:
        """Create section for System Intelligence and Performance"""
        elements = []
        
        # Section title
        title = Paragraph("AI Intelligence & System Performance", self.styles['CustomSubtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.1*inch))
        
        # Extract quality results
        q = assessment.get('quality_score', {})
        score = q.get('score', '---')
        plane_acc = q.get('plane_accuracy', '---')
        ai_conf = q.get('avg_confidence', '---')
        proc_time = analysis_data.get('processing_time', '---')
        
        data = [
            ['Anatomical Quality Score', f"{score}/100", 'Overall plane validity and detection quality'],
            ['Plane Accuracy', f"{plane_acc}", 'Geometric orientation and symmetry coefficient'],
            ['AI Confidence', f"{ai_conf}", 'Statistical reliability of anatomical segmentation'],
            ['Processing Latency', f"{proc_time}s", 'Real-time inference execution speed']
        ]
        
        table = Table(data, colWidths=[2.2*inch, 1.0*inch, 3.3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['primary']),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, -1), self.colors['light_gray']),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements

    def _create_footer(self) -> List:
        """Create report footer"""
        elements = []
        
        elements.append(Spacer(1, 0.3*inch))
        
        footer_text = """
        <i>This report is generated by CradleMetrics AI-powered fetal biometry analysis system. 
        All measurements and assessments should be reviewed by a qualified healthcare professional. 
        This report is for clinical decision support and should not replace professional medical judgment.</i>
        """
        para = Paragraph(footer_text, self.styles['Normal'])
        elements.append(para)
        
        return elements
    
    def _add_page_number(self, canvas, doc):
        """Add page number to each page"""
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(7.5*inch, 0.5*inch, text)
        canvas.drawString(1*inch, 0.5*inch, "CradleMetrics Clinical Report")
        canvas.restoreState()


# Example usage
if __name__ == "__main__":
    from clinical_rules import ClinicalRulesEngine
    from recommendations import RecommendationGenerator
    
    # Sample data
    sample_data = {
        'HC': {'value': 245, 'percentile': 50},
        'AC': {'value': 289, 'percentile': 52},
        'BPD': {'value': 75, 'percentile': 48},
        'FL': {'value': 65, 'percentile': 51},
        'GA': {'value': 28.3}
    }
    
    # Generate assessment and recommendations
    engine = ClinicalRulesEngine()
    rec_gen = RecommendationGenerator()
    
    assessment = engine.generate_comprehensive_assessment(sample_data)
    recommendations = rec_gen.generate_recommendations(assessment)
    
    # Generate PDF report
    report_gen = ClinicalReportGenerator()
    pdf_path = report_gen.generate_report(sample_data, assessment, recommendations)
    
    print(f"Report generated: {pdf_path}")
