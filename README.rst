simpy-events
============  

|license| |python version| |build-status| |docs| |coverage| |pypi package|

.. |license| image:: https://img.shields.io/github/license/loicpw/simpy-events.svg
.. |build-status| image:: https://travis-ci.org/loicpw/simpy-events.svg?branch=master
    :target: https://travis-ci.org/loicpw/simpy-events
.. |docs| image:: https://readthedocs.org/projects/simpy-events/badge/?version=latest
    :target: http://simpy-events.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status
.. |coverage| image:: https://coveralls.io/repos/github/loicpw/simpy-events/badge.svg?branch=master
    :target: https://coveralls.io/github/loicpw/simpy-events?branch=master
.. |pypi package| image:: https://badge.fury.io/py/simpy-events.svg
    :target: https://badge.fury.io/py/simpy-events
.. |python version| image:: https://img.shields.io/pypi/pyversions/simpy-events.svg
   :target: https://pypi.python.org/pypi/simpy-events

event system with simpy to decouple simulation code and increase reusability

install and test
=======================

install from pypi
********************

using pip:

.. code-block:: bash

    $ pip install simpy-events

dev install
****************

There is a makefile in the project root directory:
    
.. code-block:: bash

    $ make dev

Using pip, the above is equivalent to:

.. code-block:: bash

    $ pip install -r requirements-dev.txt                                             
    $ pip install -e .

run the tests
******************

Use the makefile in the project root directory:

.. code-block:: bash

    $ make test

This runs the tests generating a coverage html report

build the doc
******************

The documentation is made with sphinx, you can use the makefile in the
project root directory to build html doc:

.. code-block:: bash

    $ make doc

Documentation
=======================

Documentation on `Read The Docs`_.

Meta
=======================

loicpw - peronloic.us@gmail.com

Distributed under the MIT license. See ``LICENSE.txt`` for more information.

https://github.com/loicpw


.. _Read The Docs: http://simpy-events.readthedocs.io/en/latest/

