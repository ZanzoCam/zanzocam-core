"""
setup.py for zanzocam.
For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""
import os
from pathlib import Path
from setuptools import setup, find_packages


with (Path(__file__).parent.absolute() / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()
    
    
REQUIREMENTS: dict = {
    'base': [
        "setuptools_scm",  # for versioning
        "importlib_metadata",  # py<3.8
    ],
    'webcam': [
        "picamera",
        "Pillow",
        "requests",
    ],
    'web-ui': [
        "Flask",
        "matplotlib",
        #"pandas",
        "numpy",
    ]
}

setup(
    name='zanzocam',
    author='Sara Zanzottera',
    author_email='',
    description='ZANZOCAM - remote, asynchronous, low frequency webcam for isolated locations and long-term autonomous monitoring',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://zansara.github.io/zanzocam/',

    setup_requires=['setuptools_scm'],
    use_scm_version={"root": "..", "relative_to": os.path.dirname(__file__)},
    
    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],

    install_requires=REQUIREMENTS['base'],
    extras_require={
        **REQUIREMENTS,
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
    entry_points={
        'console_scripts': [
            'z-webcam=webcam.main:main',
            'z-calibrate=webcam.main:calibrate',
            'z-ui=web_ui.endpoints:main',
        ],
    },
)
