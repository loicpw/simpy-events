#!/usr/bin/env python
import pytest
from simpy_events.manager import RootNameSpace
#from simpy_events.event import EventDispatcher
import simpy
import sys


@pytest.fixture
def env():
    yield simpy.Environment()


@pytest.fixture
def root():
#    class Dispatcher(EventDispatcher):
#        def __init__(self):
#            self.verbose = False
#
#        def dispatch(self, event, hook, data):
#            if self.verbose:
#                metadata = {key: str(item) for key, item
#                            in event.metadata.items()}
#                try:
#                    # data is a simpy event
#                    print('dispatching', metadata, hook, data.value)
#                except AttributeError:
#                    # data is something else
#                    print('dispatching', metadata, hook, data)
#            super().dispatch(event, hook, data)
#
#    return RootNameSpace(dispatcher=Dispatcher())
    return RootNameSpace()


def test_example_1(root, env, capsys):

    # satellite ------------------------------------------------------ #
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

    # receiver ------------------------------------------------------- #
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
         
    # analyse -------------------------------------------------------- #
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
    
    # ---------------------------------------------------------------- #
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
    # ---------------------------------------------------------------- #

    run(env)
    captured = capsys.readouterr()
    print('test_example_1:\n', file=sys.stderr)
    print(captured.out, file=sys.stderr)
    assert captured.out == """\
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
"""
