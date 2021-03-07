"""
setup.py for zanzocam-webcam.
For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""
import os
from pathlib import Path
from setuptools import setup, find_packages
from setuptools_scm import get_version


HERE = Path(__file__).parent.absolute()
with (HERE / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()
    
    
REQUIREMENTS: dict = {
    'core': [
        "picamera",
        "Pillow",
        "requests",
        "setuptools_scm",  # for versioning
        "importlib_metadata",  # py<3.8
    ],
    'test': [
        "pytest",
        "pytest-cov",
        "pytest-random-order",
    ],
}


setup(
    name='zanzocam-webcam',
    version=get_version(),
    
    use_scm_version = {
        "root": "..",
        "relative_to": __file__,
    },
    setup_requires=['setuptools_scm'],


    author='Sara Zanzottera',
    author_email='',
    description='ZANZOCAM (Webcam module)',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://zansara.github.io/zanzocam/',

    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],

    install_requires=REQUIREMENTS['core'],
    extras_require={
        **REQUIREMENTS,
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
    entry_points={
        'console_scripts': [
            'z-webcam=webcam.main:main',
        ],
    },

)
