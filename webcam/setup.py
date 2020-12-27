"""
setup.py for zanzocam-webcam.
For reference see
https://packaging.python.org/guides/distributing-packages-using-setuptools/
"""
from pathlib import Path
from setuptools import setup, find_packages


HERE = Path(__file__).parent.absolute()
with (HERE / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()


REQUIREMENTS: dict = {
    'core': [
        "picamera",
        "Pillow",
        "requests",
    ],
    'test': [
        "pytest",
        "pytest-cov",
        "pytest-random-order",
    ],
}


setup(
    name='zanzocam_webcam',
    version="0.0.1",

    author='Sara Zanzottera',
    author_email='',
    description='ZANZOCAM (Webcam module)',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='',

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
