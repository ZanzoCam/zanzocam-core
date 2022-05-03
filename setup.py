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
    'deploy': [
        "picamera",
        "Pillow",
        "requests",
        "piexif",  # Carry over and edit EXIF information

        "uwsgi",
        "Flask"
    ],
    'test-on-rpi': [
        "picamera",
        'Pillow',
        'requests',
        'piexif',
        
        'pytest',
        'pytest-coverage',
        'pytest-subprocess',
        'freezegun',  # Mock datetime objects
    ],
    'ci': [
        'Pillow',
        'requests',
        'piexif',
        
        'pytest',
        'pytest-coverage',
        'pytest-subprocess',
        'freezegun',  # Mock datetime objects
        'coveralls',  # To publish the coverage data on coveralls
    ],
    'docs': [
        'sphinx',
        'sphinx-rtd-theme',
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
    include_package_data=True,
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    setup_requires=['wheel'],
    install_requires=[],
    extras_require={
        **REQUIREMENTS,
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
    entry_points={
        'console_scripts': [
            'z-webcam=zanzocam.webcam.main:main',
            'z-ui=zanzocam.web_ui.endpoints:main',
        ],
    },
)
