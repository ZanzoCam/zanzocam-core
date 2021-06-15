# ZanzoCam - Python module

[![CodeQL](https://github.com/ZanSara/zanzocam/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/ZanSara/zanzocam/actions/workflows/codeql-analysis.yml)   [![Unit Tests](https://github.com/ZanSara/zanzocam/actions/workflows/ci.yml/badge.svg)](https://github.com/ZanSara/zanzocam/actions/workflows/ci.yml) [![Coverage Status](https://coveralls.io/repos/github/ZanzoCam/zanzocam-core/badge.svg)](https://coveralls.io/github/ZanzoCam/zanzocam-core)

Python module of ZanzoCam, a remote camera for autonomous operation in isolated locations, based on Raspberry Pi.

See the full documentation for this project [here](zanzocam.github.io/) and the internal docs [here](zanzocam.github.io/zanzocam-core))

## Setup

This package provides the `z-webcam` command to a Raspberry Pi OS, once all the [prerequisites](zanzocam.github.io/docs/image-creation/) are satisfied.

It can be installed on a Raspberry Pi with:
```
pip install "zanzocam[deploy] @ git+https://github.com/ZanzoCam/zanzocam-core.git"
```

## Tests

Tests should be run on a Raspberry Pi, but the unit tests can be run also on another machine or on a CI. 

To make a test install on a Raspberry Pi, run:
```
git clone https://github.com/zanzocam/zanzocam-core.git
cd zanzocam-core
pip install -e .[test-on-rpi]
pytest
```

## Docs

To build the docs, first install the dependencies (on any machine) with:
```
pip install "zanzocam[docs] @ git+https://github.com/ZanzoCam/zanzocam-core.git"
```
Then move into the `docs` and execute:
```
make html
```
You will get the resulting doc pages under `build/html`.

## Contribute

This project is young and we have no definite contributing guidelines yet. Open an issue, make a  small PR or get in touch with the developers at zanzocam@gmail.com before investing a lot of time into a feature or a bugfix.

As a starting point, here are my current guidelines:

- The system must stay small and simple.
- The system must stay monolithic and fully executable on the Raspberry (no server components here, see [this repo](https://github.com/ZanzoCam/zanzocam-control-panel) if you want to improve the server side).
- Always make sure all tests pass before sending a PR.
- Keep the code tidy, short and heavily commented.
- ZanzoCam must support Raspberry Pi Camera v2 and HQ from a Raspberry Pi Zero W in its base version.

## Get in touch

You can reach out at zanzocam@gmail.com for any question or remark that doesn't fit as a GitHub issue.
