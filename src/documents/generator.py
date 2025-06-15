"""
Document Generator - Create formatted documents with video summaries
Supports TXT, DOCX, and PDF formats
"""

import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Document generation libraries
from docx import Document
from docx.shared import Inches
from docx.enum.style import WD_STYLE_TYPE
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from config.settings import get_settings
from utils.validators import sanitize_filename

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentGenerator:
    """Generate formatted documents with video summaries."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "yt_summarizer_docs"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def create_document(
        self, 
        video_data: Dict, 
        summary_data: Dict, 
        output_format: str = 'txt'
    ) -> Optional[Path]:
        """
        Create formatted document with video summary.
        
        Args:
            video_data: Processed video data
            summary_data: AI-generated summary data
            output_format: Output format ('txt', 'docx', 'pdf')
            
        Returns:
            Path to generated document or None on error
        """
        try:
            if output_format not in settings.supported_formats:
                raise ValueError(f"Unsupported format: {output_format}")
            
            # Prepare document content
            content = self._prepare_document_content(video_data, summary_data)
            
            # Generate filename
            video_title = video_data.get('video_info', {}).get('title', 'Unknown Video')
            safe_title = sanitize_filename(video_title)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{safe_title}_{timestamp}.{output_format}"
            document_path = self.temp_dir / filename
            
            # Create document based on format
            if output_format == 'txt':
                document_path = await self._create_txt_document(content, document_path)
            elif output_format == 'docx':
                document_path = await self._create_docx_document(content, document_path)
            elif output_format == 'pdf':
                document_path = await self._create_pdf_document(content, document_path)
            
            logger.info(f"Created {output_format.upper()} document: {document_path}")
            return document_path
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return None
    
    def _prepare_document_content(self, video_data: Dict, summary_data: Dict) -> Dict:
        """Prepare structured content for document generation."""
        video_info = video_data.get('video_info', {})
        transcripts = video_data.get('transcripts', {})
        summary = summary_data.get('summary', {})
        
        # Format duration
        duration = video_info.get('duration', 0)
        duration_str = f"{duration // 60}:{duration % 60:02d}"
        
        # Format date
        upload_date = video_info.get('upload_date', '')
        if upload_date and len(upload_date) >= 8:
            try:
                formatted_date = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[:4]}"
            except:
                formatted_date = upload_date
        else:
            formatted_date = upload_date or 'Unknown'
        
        return {
            'title': f"YouTube Video Summary: {video_info.get('title', 'Unknown Title')}",
            'video_info': {
                'title': video_info.get('title', 'Unknown Title'),
                'uploader': video_info.get('uploader', 'Unknown'),
                'duration': duration_str,
                'upload_date': formatted_date,
                'video_id': video_info.get('id', ''),
                'view_count': f"{video_info.get('view_count', 0):,}" if video_info.get('view_count') else 'Unknown'
            },
            'summary': {
                'executive_summary': summary.get('executive_summary', 'No executive summary available.'),
                'key_points': summary.get('key_points', []),
                'detailed_summary': summary.get('detailed_summary', 'No detailed summary available.'),
                'timestamps': summary.get('timestamps', []),
                'takeaways': summary.get('takeaways', [])
            },
            'transcript_info': {
                'available': bool(transcripts.get('transcripts')),
                'language': transcripts.get('language', 'Unknown'),
                'is_generated': transcripts.get('is_generated', None),
                'total_segments': transcripts.get('total_segments', 0)
            },
            'ai_info': {
                'model': summary_data.get('ai_model', settings.openai_model),
                'tokens_used': summary_data.get('tokens_used', 0),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        }
    
    async def _create_txt_document(self, content: Dict, output_path: Path) -> Path:
        """Create plain text document."""
        def generate_txt():
            lines = []
            
            # Header
            lines.append("=" * 80)
            lines.append(content['title'])
            lines.append("=" * 80)
            lines.append("")
            
            # Video Information
            lines.append("VIDEO INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Title: {content['video_info']['title']}")
            lines.append(f"Channel: {content['video_info']['uploader']}")
            lines.append(f"Duration: {content['video_info']['duration']}")
            lines.append(f"Upload Date: {content['video_info']['upload_date']}")
            lines.append(f"Video ID: {content['video_info']['video_id']}")
            lines.append(f"View Count: {content['video_info']['view_count']}")
            lines.append("")
            
            # Executive Summary
            lines.append("EXECUTIVE SUMMARY")
            lines.append("-" * 40)
            lines.append(content['summary']['executive_summary'])
            lines.append("")
            
            # Key Points
            if content['summary']['key_points']:
                lines.append("KEY POINTS")
                lines.append("-" * 40)
                for i, point in enumerate(content['summary']['key_points'], 1):
                    lines.append(f"{i}. {point}")
                lines.append("")
            
            # Detailed Summary
            if content['summary']['detailed_summary']:
                lines.append("DETAILED SUMMARY")
                lines.append("-" * 40)
                lines.append(content['summary']['detailed_summary'])
                lines.append("")
            
            # Important Timestamps
            if content['summary']['timestamps']:
                lines.append("IMPORTANT TIMESTAMPS")
                lines.append("-" * 40)
                for timestamp in content['summary']['timestamps']:
                    lines.append(f"• {timestamp}")
                lines.append("")
            
            # Takeaways
            if content['summary']['takeaways']:
                lines.append("KEY TAKEAWAYS")
                lines.append("-" * 40)
                for takeaway in content['summary']['takeaways']:
                    lines.append(f"• {takeaway}")
                lines.append("")
            
            # Transcript Information
            lines.append("TRANSCRIPT INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Available: {'Yes' if content['transcript_info']['available'] else 'No'}")
            if content['transcript_info']['available']:
                lines.append(f"Language: {content['transcript_info']['language']}")
                lines.append(f"Type: {'Auto-generated' if content['transcript_info']['is_generated'] else 'Manual'}")
                lines.append(f"Total Segments: {content['transcript_info']['total_segments']}")
            lines.append("")
            
            # AI Generation Info
            lines.append("SUMMARY GENERATION INFO")
            lines.append("-" * 40)
            lines.append(f"AI Model: {content['ai_info']['model']}")
            lines.append(f"Tokens Used: {content['ai_info']['tokens_used']}")
            lines.append(f"Generated: {content['ai_info']['generated_at']}")
            lines.append("")
            
            # Footer
            lines.append("=" * 80)
            lines.append(f"Generated by {settings.bot_name} v{settings.bot_version}")
            lines.append("=" * 80)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_txt)
        return output_path
    
    async def _create_docx_document(self, content: Dict, output_path: Path) -> Path:
        """Create Microsoft Word document."""
        def generate_docx():
            doc = Document()
            
            # Title
            title = doc.add_heading(content['title'], 0)
            title.alignment = 1  # Center alignment
            
            # Video Information Section
            doc.add_heading('Video Information', level=1)
            
            # Create a table for video info
            table = doc.add_table(rows=6, cols=2)
            table.style = 'Table Grid'
            
            info_items = [
                ('Title', content['video_info']['title']),
                ('Channel', content['video_info']['uploader']),
                ('Duration', content['video_info']['duration']),
                ('Upload Date', content['video_info']['upload_date']),
                ('Video ID', content['video_info']['video_id']),
                ('View Count', content['video_info']['view_count'])
            ]
            
            for i, (label, value) in enumerate(info_items):
                table.cell(i, 0).text = label
                table.cell(i, 1).text = str(value)
            
            # Executive Summary
            doc.add_heading('Executive Summary', level=1)
            doc.add_paragraph(content['summary']['executive_summary'])
            
            # Key Points
            if content['summary']['key_points']:
                doc.add_heading('Key Points', level=1)
                for point in content['summary']['key_points']:
                    doc.add_paragraph(point, style='List Bullet')
            
            # Detailed Summary
            if content['summary']['detailed_summary']:
                doc.add_heading('Detailed Summary', level=1)
                doc.add_paragraph(content['summary']['detailed_summary'])
            
            # Important Timestamps
            if content['summary']['timestamps']:
                doc.add_heading('Important Timestamps', level=1)
                for timestamp in content['summary']['timestamps']:
                    doc.add_paragraph(timestamp, style='List Bullet')
            
            # Key Takeaways
            if content['summary']['takeaways']:
                doc.add_heading('Key Takeaways', level=1)
                for takeaway in content['summary']['takeaways']:
                    doc.add_paragraph(takeaway, style='List Bullet')
            
            # Technical Information
            doc.add_heading('Technical Information', level=1)
            
            tech_info = doc.add_paragraph()
            tech_info.add_run('Transcript Available: ').bold = True
            tech_info.add_run('Yes' if content['transcript_info']['available'] else 'No')
            tech_info.add_run('\n')
            
            if content['transcript_info']['available']:
                tech_info.add_run('Language: ').bold = True
                tech_info.add_run(content['transcript_info']['language'])
                tech_info.add_run('\n')
                tech_info.add_run('Type: ').bold = True
                tech_info.add_run('Auto-generated' if content['transcript_info']['is_generated'] else 'Manual')
                tech_info.add_run('\n')
            
            tech_info.add_run('AI Model: ').bold = True
            tech_info.add_run(content['ai_info']['model'])
            tech_info.add_run('\n')
            tech_info.add_run('Tokens Used: ').bold = True
            tech_info.add_run(str(content['ai_info']['tokens_used']))
            tech_info.add_run('\n')
            tech_info.add_run('Generated: ').bold = True
            tech_info.add_run(content['ai_info']['generated_at'])
            
            # Footer
            doc.add_page_break()
            footer_para = doc.add_paragraph()
            footer_para.alignment = 1  # Center alignment
            footer_run = footer_para.add_run(f"Generated by {settings.bot_name} v{settings.bot_version}")
            footer_run.italic = True
            
            # Save document
            doc.save(output_path)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_docx)
        return output_path
    
    async def _create_pdf_document(self, content: Dict, output_path: Path) -> Path:
        """Create PDF document."""
        def generate_pdf():
            doc = SimpleDocTemplate(str(output_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                alignment=1,  # Center
                spaceAfter=30
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor='#2E74B5',
                spaceAfter=12
            )
            
            # Title
            story.append(Paragraph(content['title'], title_style))
            story.append(Spacer(1, 20))
            
            # Video Information
            story.append(Paragraph('Video Information', heading_style))
            
            video_info_text = f"""
            <b>Title:</b> {content['video_info']['title']}<br/>
            <b>Channel:</b> {content['video_info']['uploader']}<br/>
            <b>Duration:</b> {content['video_info']['duration']}<br/>
            <b>Upload Date:</b> {content['video_info']['upload_date']}<br/>
            <b>Video ID:</b> {content['video_info']['video_id']}<br/>
            <b>View Count:</b> {content['video_info']['view_count']}
            """
            story.append(Paragraph(video_info_text, styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Executive Summary
            story.append(Paragraph('Executive Summary', heading_style))
            story.append(Paragraph(content['summary']['executive_summary'], styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Key Points
            if content['summary']['key_points']:
                story.append(Paragraph('Key Points', heading_style))
                for point in content['summary']['key_points']:
                    story.append(Paragraph(f"• {point}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Detailed Summary
            if content['summary']['detailed_summary']:
                story.append(Paragraph('Detailed Summary', heading_style))
                story.append(Paragraph(content['summary']['detailed_summary'], styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Important Timestamps
            if content['summary']['timestamps']:
                story.append(Paragraph('Important Timestamps', heading_style))
                for timestamp in content['summary']['timestamps']:
                    story.append(Paragraph(f"• {timestamp}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Key Takeaways
            if content['summary']['takeaways']:
                story.append(Paragraph('Key Takeaways', heading_style))
                for takeaway in content['summary']['takeaways']:
                    story.append(Paragraph(f"• {takeaway}", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Technical Information
            story.append(Paragraph('Technical Information', heading_style))
            
            tech_text = f"""
            <b>Transcript Available:</b> {'Yes' if content['transcript_info']['available'] else 'No'}<br/>
            """
            
            if content['transcript_info']['available']:
                tech_text += f"""
                <b>Language:</b> {content['transcript_info']['language']}<br/>
                <b>Type:</b> {'Auto-generated' if content['transcript_info']['is_generated'] else 'Manual'}<br/>
                """
            
            tech_text += f"""
            <b>AI Model:</b> {content['ai_info']['model']}<br/>
            <b>Tokens Used:</b> {content['ai_info']['tokens_used']}<br/>
            <b>Generated:</b> {content['ai_info']['generated_at']}
            """
            
            story.append(Paragraph(tech_text, styles['Normal']))
            story.append(Spacer(1, 40))
            
            # Footer
            footer_text = f"Generated by {settings.bot_name} v{settings.bot_version}"
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                alignment=1,  # Center
                textColor='#666666'
            )
            story.append(Paragraph(footer_text, footer_style))
            
            # Build PDF
            doc.build(story)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_pdf)
        return output_path
    
    async def cleanup_old_documents(self, max_age_hours: int = 24):
        """Clean up old temporary documents."""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)
            
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logger.debug(f"Cleaned up old document: {file_path}")
                    except Exception as e:
                        logger.warning(f"Could not delete {file_path}: {e}")
                        
        except Exception as e:
            logger.error(f"Error during document cleanup: {e}") 