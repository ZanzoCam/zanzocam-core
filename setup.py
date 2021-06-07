import os
from pathlib import Path
from setuptools import setup, find_packages

with (Path(__file__).parent.absolute() / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()

with (Path(__file__).parent.absolute() / 'zanzocam' / 'constants.py').open('r') as cs:
    for line in cs.readlines():
        if line.startswith("VERSION"):
            VERSION = line.replace("VERSION", "").replace("=", "").replace('"', "").replace(" ", "").replace("\n", "")
            break
REQUIREMENTS: dict = {
    'webcam': [
        "picamera",
        "Pillow",
        "requests",
        "piexif",  # Carry over and edit EXIF information
    ],
    'web-ui': [
        "picamera",
        "uwsgi",
        "Flask"
    ],
    'test': [
        'pytest',
        'pytest-coverage',
        'pytest-subprocess',
        'freezegun',  # Mock datetime objects
    ]
}

setup(
    name='zanzocam',
    version=VERSION,
    author='Sara Zanzottera',
    author_email='zanzocam@gmail.com',
    description='ZANZOCAM - remote, asynchronous, low frequency webcam for isolated locations and long-term autonomous monitoring',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://zanzocam.github.io/',

    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=[],
    extras_require={
        **REQUIREMENTS,
        'deploy': [req for reqs in [REQUIREMENTS['webcam'], REQUIREMENTS['web-ui']] for req in reqs],
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
    entry_points={
        'console_scripts': [
            'z-webcam=zanzocam.webcam.main:main',
            'z-ui=zanzocam.web_ui.endpoints:main',
        ],
    },
)
