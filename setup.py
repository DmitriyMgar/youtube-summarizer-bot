"""
Setup script for YouTube Video Summarizer Bot
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="youtube-summarizer-bot",
    version="1.0.0",
    author="YouTube Summarizer Bot Team",
    author_email="contact@example.com",
    description="AI-powered YouTube video summarization bot for Telegram",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/youtube-summarizer-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=8.2.0",
            "pytest-asyncio>=0.23.7",
            "pytest-mock>=3.14.0",
            "black>=24.4.2",
            "flake8>=7.1.0",
            "mypy>=1.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "youtube-summarizer-bot=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords="telegram bot youtube summarization ai openai gpt video transcript",
    project_urls={
        "Bug Reports": "https://github.com/example/youtube-summarizer-bot/issues",
        "Source": "https://github.com/example/youtube-summarizer-bot",
        "Documentation": "https://github.com/example/youtube-summarizer-bot/blob/main/README.md",
    },
) 