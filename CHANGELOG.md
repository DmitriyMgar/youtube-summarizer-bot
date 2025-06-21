# Changelog

## [Upcoming] - 2024-12-19

### Added
- **Format selection for subtitle commands**: Added support for output format selection in `/raw_subtitles` and `/corrected_subtitles` commands
  - Supported formats: txt, docx, pdf
  - Usage: `/corrected_subtitles <URL> format:pdf` or `/raw_subtitles <URL> format:docx`
  - Default format can be configured in settings
- **New subtitle document generator**: Created specialized document generator for subtitles with proper formatting
  - Supports all three formats (TXT, DOCX, PDF) with proper styling
  - Includes video metadata, subtitle content with timestamps
  - Maintains Unicode support for Cyrillic characters in PDF format

### Changed
- **Updated command parsing**: Both subtitle commands now use `context.args` instead of manual text parsing
- **Enhanced error handling**: Better format validation and error messages
- **Improved user messages**: Updated usage instructions to include format selection examples

### Optimized
- **Reduced code duplication in DocumentGenerator**: 
  - Extracted common PDF styles into `_get_pdf_styles()` method
  - Created unified `_run_in_executor()` method for async operations
  - Standardized filename generation with `_generate_filename()` method
  - Added common PDF footer creation with `_add_pdf_footer()` method
  - Reduced file size by ~150 lines while maintaining all functionality

### Technical Details
- Added `create_subtitles_document()` method to `DocumentGenerator` class
- Added `_prepare_subtitle_content()`, `_create_txt_subtitles_document()`, `_create_docx_subtitles_document()`, `_create_pdf_subtitles_document()` methods
- Updated localization messages for both Russian and English
- Maintained backward compatibility - commands work without format specification

### Fixed
- Consistent argument parsing across all bot commands
- Proper file cleanup after document generation 

## [1.0.1] - 2024-01-XX

### Added
- Format selection support for `/corrected_subtitles` and `/raw_subtitles` commands
- Support for TXT, DOCX, and PDF formats in subtitle commands
- New `DocumentGenerator.create_subtitles_document()` method for subtitle document generation
- Format-specific methods for creating subtitle documents in different formats
- Proper localization for subtitle command usage messages

### Changed
- Modified `/corrected_subtitles` and `/raw_subtitles` commands to parse format from context.args
- Updated command handlers to use DocumentGenerator instead of simple text files
- Enhanced error handling and validation for format specification
- Improved file naming and metadata handling for subtitle documents

### Fixed
- Backward compatibility maintained for commands without format specification (defaults to TXT)

### Optimized
- **Code Deduplication**: Consolidated document creation methods by merging duplicate methods
  - Combined `_create_txt_document` and `_create_txt_subtitles_document` into unified `_create_txt_document`
  - Combined `_create_docx_document` and `_create_docx_subtitles_document` into unified `_create_docx_document`  
  - Combined `_create_pdf_document` and `_create_pdf_subtitles_document` into unified `_create_pdf_document`
  - Added `_detect_content_type()` method to automatically determine content type (summary/subtitles)
  - Reduced code by ~200 lines while maintaining full functionality
  - Added deprecated wrapper methods for backward compatibility

### Technical Details
- Format syntax: `/corrected_subtitles <URL> format:pdf`
- Supported formats: `txt`, `docx`, `pdf`
- Default format: `txt` (if not specified)
- Documents include video metadata, subtitle content, and generation information 