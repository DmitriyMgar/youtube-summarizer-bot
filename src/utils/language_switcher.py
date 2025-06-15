"""
Language switcher utility for testing localization
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from localization import set_language, get_message

def test_language(lang_code: str):
    """Test messages in a specific language."""
    print(f"\n=== Testing {lang_code.upper()} Language ===")
    
    set_language(lang_code)
    
    # Test some key messages
    test_messages = [
        ("welcome_message", {
            "bot_name": "YouTube Summarizer Bot",
            "bot_version": "1.0.0",
            "first_name": "Test User",
            "supported_formats": "txt, docx, pdf"
        }),
        ("error_invalid_url", {}),
        ("processing_ai_summary", {}),
        ("success_queued", {
            "video_id": "test123",
            "output_format": "PDF"
        }),
        ("formats_title", {}),
        ("commands.start", {}),
        ("commands.help", {})
    ]
    
    for message_key, kwargs in test_messages:
        try:
            message = get_message(message_key, **kwargs)
            print(f"\n{message_key}:")
            print(message[:100] + "..." if len(message) > 100 else message)
        except Exception as e:
            print(f"\nError with {message_key}: {e}")

def main():
    """Main function to test both languages."""
    print("YouTube Summarizer Bot - Language Test")
    print("=" * 50)
    
    # Test Russian (default)
    test_language("ru")
    
    # Test English (fallback)
    test_language("en")
    
    print("\n" + "=" * 50)
    print("Language test completed!")

if __name__ == "__main__":
    main() 