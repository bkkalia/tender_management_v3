"""
Tender Management Utility v3.2
Professional tender data management with advanced search, filtering, and visualization.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
def read_requirements(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="tender-management-utility",
    version="3.2.0",
    author="Cloud84 Development",
    author_email="contact@cloud84.in",
    description="Professional tender data management with advanced search, filtering, and visualization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cloud84/tender-management-utility",
    project_urls={
        "Bug Tracker": "https://github.com/cloud84/tender-management-utility/issues",
        "Documentation": "https://github.com/cloud84/tender-management-utility/docs",
        "Source Code": "https://github.com/cloud84/tender-management-utility",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Utilities",
    ],
    keywords="tender management procurement data analysis search filter visualization",
    packages=find_packages(exclude=['tests', 'benchmark', 'docs', 'scripts', 'tools']),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': read_requirements('requirements-dev.txt'),
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
        ],
        'lint': [
            'flake8>=6.0.0',
            'black>=23.0.0',
            'isort>=5.12.0',
        ],
        'security': [
            'bandit>=1.7.0',
            'safety>=2.3.0',
        ],
        'docs': [
            'mkdocs>=1.4.0',
            'mkdocs-material>=9.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'tender-management=main:main',
            'tmu=main:main',  # Short alias
        ],
        'gui_scripts': [
            'tender-management-gui=main:main',
        ],
    },
    data_files=[
        ('share/applications', ['resources/tender-management.desktop']),
        ('share/icons/hicolor/256x256/apps', ['resources/icon.png']),
    ],
    zip_safe=False,
    test_suite='tests',
    tests_require=[
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
    ],
)
