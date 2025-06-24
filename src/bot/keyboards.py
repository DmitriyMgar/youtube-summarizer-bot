"""
YouTube Video Summarizer Bot - Interactive Keyboards
Provides inline keyboards for user interaction in dialog-based interface
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional

from config.settings import get_settings
from src.localization.messages import get_message, get_messages

def get_message_or_default(key: str, default: str = "") -> str:
    """Get message or return default if key not found."""
    messages = get_messages()
    keys = key.split('.')
    message = messages
    for k in keys:
        if isinstance(message, dict) and k in message:
            message = message[k]
        else:
            return default
    return message if isinstance(message, str) else default

settings = get_settings()


class InteractiveKeyboards:
    """Factory class for creating interactive keyboards."""
    
    @staticmethod
    def get_operation_selection_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard for operation selection."""
        keyboard = [
            [
                InlineKeyboardButton(
                    get_message_or_default("btn_summarize", "📄 Summarize"), 
                    callback_data="op_summarize"
                ),
                InlineKeyboardButton(
                    get_message_or_default("btn_raw_subtitles", "📝 Raw Subtitles"), 
                    callback_data="op_raw_subtitles"
                )
            ],
            [
                InlineKeyboardButton(
                    get_message_or_default("btn_corrected_subtitles", "✨ Corrected Subtitles"), 
                    callback_data="op_corrected_subtitles"
                )
            ],
            [
                InlineKeyboardButton(
                    get_message_or_default("btn_cancel", "❌ Cancel"), 
                    callback_data="op_cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_format_selection_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard for format selection."""
        keyboard = []
        
        # Create format buttons based on supported formats
        format_buttons = []
        for format_type in settings.supported_formats_list:
            if format_type == 'txt':
                button_text = get_message_or_default("btn_format_txt", "📄 TXT")
            elif format_type == 'docx':
                button_text = get_message_or_default("btn_format_docx", "📑 DOCX")
            elif format_type == 'pdf':
                button_text = get_message_or_default("btn_format_pdf", "📕 PDF")
            else:
                button_text = f"📄 {format_type.upper()}"
            
            format_buttons.append(
                InlineKeyboardButton(button_text, callback_data=f"fmt_{format_type}")
            )
        
        # Group format buttons (max 3 per row)
        for i in range(0, len(format_buttons), 3):
            keyboard.append(format_buttons[i:i+3])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton(
                get_message_or_default("btn_back", "⬅️ Back"), 
                callback_data="back_to_operations"
            ),
            InlineKeyboardButton(
                get_message_or_default("btn_cancel", "❌ Cancel"), 
                callback_data="op_cancel"
            )
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_processing_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard during processing."""
        keyboard = [
            [
                InlineKeyboardButton(
                    get_message_or_default("btn_cancel_processing", "❌ Cancel Processing"), 
                    callback_data="cancel_processing"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_error_retry_keyboard(error_type: str = "general") -> InlineKeyboardMarkup:
        """Create keyboard for error handling with retry option."""
        keyboard = []
        
        if error_type in ["network", "temporary"]:
            keyboard.append([
                InlineKeyboardButton("🔄 Retry", callback_data="retry_processing"),
                InlineKeyboardButton("❌ Cancel", callback_data="op_cancel")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("❌ Cancel", callback_data="op_cancel")
            ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
        """Create confirmation keyboard for important actions."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
                InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_minimal_cancel_keyboard() -> InlineKeyboardMarkup:
        """Create minimal keyboard with just cancel button."""
        keyboard = [
            [
                InlineKeyboardButton(
                    get_message_or_default("btn_cancel", "❌ Cancel"), 
                    callback_data="op_cancel"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
        
    @staticmethod
    def get_quality_selection_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard for quality selection (future feature)."""
        keyboard = [
            [
                InlineKeyboardButton("🔥 High Quality", callback_data="quality_high"),
                InlineKeyboardButton("⚡ Fast", callback_data="quality_fast")
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="back_to_formats"),
                InlineKeyboardButton("❌ Cancel", callback_data="op_cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_help_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard for help and support options."""
        keyboard = [
            [
                InlineKeyboardButton("❓ Help", callback_data="show_help"),
                InlineKeyboardButton("📋 Commands", callback_data="show_commands")
            ],
            [
                InlineKeyboardButton("🆔 Support", callback_data="show_support"),
                InlineKeyboardButton("❌ Close", callback_data="close_help")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)


class KeyboardUtils:
    """Utility functions for keyboard operations."""
    
    @staticmethod
    def add_cancel_button(keyboard: InlineKeyboardMarkup) -> InlineKeyboardMarkup:
        """Add cancel button to existing keyboard."""
        buttons = keyboard.inline_keyboard
        cancel_row = [
            InlineKeyboardButton(
                get_message_or_default("btn_cancel", "❌ Cancel"), 
                callback_data="op_cancel"
            )
        ]
        buttons.append(cancel_row)
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def create_paginated_keyboard(
        items: list, 
        page: int = 0, 
        items_per_page: int = 5,
        callback_prefix: str = "select"
    ) -> InlineKeyboardMarkup:
        """Create paginated keyboard for long lists."""
        keyboard = []
        
        # Calculate pagination
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_items = items[start_idx:end_idx]
        
        # Add item buttons
        for i, item in enumerate(page_items):
            if isinstance(item, dict):
                text = item.get('text', f'Item {start_idx + i + 1}')
                callback_data = f"{callback_prefix}_{item.get('id', start_idx + i)}"
            else:
                text = str(item)
                callback_data = f"{callback_prefix}_{start_idx + i}"
            
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        # Add pagination controls
        pagination_row = []
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page - 1}")
            )
        
        if end_idx < len(items):
            pagination_row.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 1}")
            )
        
        if pagination_row:
            keyboard.append(pagination_row)
        
        # Add cancel button
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="op_cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_operation_display_name(operation: str) -> str:
        """Get localized display name for operation."""
        operation_names = {
            'summarize': get_message_or_default("operation_summarize", "Summarization"),
            'raw_subtitles': get_message_or_default("operation_raw_subtitles", "Raw Subtitles"),
            'corrected_subtitles': get_message_or_default("operation_corrected_subtitles", "Corrected Subtitles")
        }
        return operation_names.get(operation, operation.title())
    
    @staticmethod
    def get_format_display_name(format_type: str) -> str:
        """Get localized display name for format."""
        format_names = {
            'txt': 'TXT',
            'docx': 'DOCX', 
            'pdf': 'PDF'
        }
        return format_names.get(format_type, format_type.upper())
    
    @staticmethod
    def get_operation_emoji(operation: str) -> str:
        """Get emoji for operation type."""
        operation_emojis = {
            'summarize': '📄',
            'raw_subtitles': '📝',
            'corrected_subtitles': '✨'
        }
        return operation_emojis.get(operation, '📄')
    
    @staticmethod
    def get_format_emoji(format_type: str) -> str:
        """Get emoji for format type."""
        format_emojis = {
            'txt': '📄',
            'docx': '📑',
            'pdf': '📕'
        }
        return format_emojis.get(format_type, '📄') 