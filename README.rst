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

event system with `SimPy`_ to decouple simulation code and increase reusability



( >>>>>>> **WORK IN PROGRESS** <<<<<<< )



A basic example
=======================

.. note:: `SimPy`_ is a process-based discrete-event simulation framework based on standard Python.

+ Our simplified scenario is composed of:

    - satellites emitting signals
    - receivers receiving and processing signals

+ basic imports and creating the root namespace:

 .. code-block:: python

    from simpy_events.manager import RootNameSpace
    import simpy

    root = RootNameSpace()

+ implementing a satellite model:

 .. code-block:: python

    sat = root.ns('satellite')
    
    class Satellite:
        chunk = 4
    
        def __init__(self, name, data):
            self.signal = sat.event('signal', sat=name)
            self.data = tuple(map(str, data))
    
        def process(self, env):
            signal = self.signal
            data = self.data
            chunk = self.chunk
            # slice data in chunks
            for chunk in [data[chunk*i:chunk*i+chunk]
                          for i in range(int(len(data) / chunk))]:
                event = env.timeout(1, ','.join(chunk))
                yield signal(event)

+ implementing a receiver model:

 .. code-block:: python

    receiver = root.ns('receiver')
    signals = receiver.topic('signals') 

    @signals.after
    def receive_signal(context, event):
        env = event.env
        metadata = context.event.metadata
        header = str({key: val for key, val in metadata.items()
                      if key not in ('name', 'ns')})
        env.process(process_signal(env, header, event.value))

    def process_signal(env, header, signal):
        receive = receiver.event('process')
        for data in signal.split(','):
            yield receive(env.timeout(0, f'{header}: {data}'))

+ creating code to analyse what's going on:

 .. code-block:: python

    @root.enable('analyse')
    def new_process(context, event):
        metadata = context.event.metadata
        context = {key: str(val) for key, val in metadata.items()}
        print(f'new signal process: {context}')

    @root.after('analyse')
    def signal(context, event):
        metadata = context.event.metadata
        ns = metadata['ns']
        print(f'signal: {ns.path}: {event.value}') 

+ setting up our simulation:
    
 .. code-block:: python

    root.topic('receiver::signals').extend([
        '::satellite::signal',
    ])
    root.topic('analyse').extend([
        '::satellite::signal',
        '::receiver::process',
    ])

    def run(env):
        # create some actors
        s1 = Satellite('sat1', range(8))
        s2 = Satellite('sat2', range(100, 108))
        env.process(s1.process(env))
        env.process(s2.process(env))

        # execute
        root.enabled = True
        env.run()

+ running the simulation ::

    new signal process: {'ns': '::satellite', 'name': 'signal', 'sat': 'sat1'}
    new signal process: {'ns': '::satellite', 'name': 'signal', 'sat': 'sat2'}
    signal: ::satellite: 0,1,2,3
    new signal process: {'ns': '::receiver', 'name': 'process'}
    signal: ::satellite: 100,101,102,103
    new signal process: {'ns': '::receiver', 'name': 'process'}
    signal: ::receiver: {'sat': 'sat1'}: 0
    signal: ::receiver: {'sat': 'sat2'}: 100
    signal: ::receiver: {'sat': 'sat1'}: 1
    signal: ::receiver: {'sat': 'sat2'}: 101
    signal: ::receiver: {'sat': 'sat1'}: 2
    signal: ::receiver: {'sat': 'sat2'}: 102
    signal: ::receiver: {'sat': 'sat1'}: 3
    signal: ::receiver: {'sat': 'sat2'}: 103
    signal: ::satellite: 4,5,6,7
    new signal process: {'ns': '::receiver', 'name': 'process'}
    signal: ::satellite: 104,105,106,107
    new signal process: {'ns': '::receiver', 'name': 'process'}
    signal: ::receiver: {'sat': 'sat1'}: 4
    signal: ::receiver: {'sat': 'sat2'}: 104
    signal: ::receiver: {'sat': 'sat1'}: 5
    signal: ::receiver: {'sat': 'sat2'}: 105
    signal: ::receiver: {'sat': 'sat1'}: 6
    signal: ::receiver: {'sat': 'sat2'}: 106
    signal: ::receiver: {'sat': 'sat1'}: 7
    signal: ::receiver: {'sat': 'sat2'}: 107

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
.. _SimPy: https://simpy.readthedocs.org
