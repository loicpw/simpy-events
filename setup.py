#! /usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

setuptools.setup(
    name="simpy_events",
    version="0.0.1",
    url="https://github.com/loicpw/simpy-events",
    download_url = "https://github.com/loicpw/simpy-events.git",

    author="Loïc Peron",
    author_email="peronloic.us@gmail.com",

    description="event system with simpy to decouple simulation code and increase reusability",
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.rst', 'HISTORY.rst']),

    packages=setuptools.find_packages(),

    install_requires=[],

    license='MIT License',
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
