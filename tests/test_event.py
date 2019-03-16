#!/usr/bin/env python

import pytest
from simpy_events.event import Event, EventDispatcher, Context
import simpy


@pytest.fixture
def env():
    yield simpy.Environment()


def test_create_context():
    c = Context(event='my event', hook='before', attr1='test')
    assert c.event == 'my event'
    assert c.hook == 'before'
    assert c.attr1 == 'test'
    

def test_create_event():
    evt = Event(name='emit signal', context='test')
    assert evt.metadata == {
        'name': 'emit signal',
        'context': 'test',
    }
    assert len(evt.topics) == 0
    assert evt.dispatcher is None
    assert evt.enabled is False


def test_event_enabled(capsys):
    evt = Event(name='cross red light')
    evt.enabled = True
    assert evt.enabled is True
    evt.enabled = False
    assert evt.enabled is False


def test_dispatcher_single_topic(capsys):
    disp = EventDispatcher()
    evt = Event(name='emit signal', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.event.metadata, context.hook, data)

    evt.topics.append({'hook': [handler]}) 
    disp.dispatch(evt, 'hook', 1234)
    captured = capsys.readouterr()
    assert captured.out == """\
{'name': 'emit signal', 'context': 'test'} hook 1234
"""


def test_dispatcher_topic_doesnt_contain_hook(capsys):
    disp = EventDispatcher()
    evt = Event(name='emit signal', context='test')
    evt.enabled = True
    evt.topics.append({})
    disp.dispatch(evt, 'hook', 1234)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_dispatcher_multiple_topic(capsys):
    disp = EventDispatcher()
    evt = Event(name='emit signal', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.event.metadata, context.hook, data)

    evt.topics.append({'hook': [handler]}) 
    evt.topics.append({'hook': [handler]}) 
    evt.topics.append({'hook': [handler]}) 

    disp.dispatch(evt, 'hook', 1234)
    captured = capsys.readouterr()
    assert captured.out == """\
{'name': 'emit signal', 'context': 'test'} hook 1234
{'name': 'emit signal', 'context': 'test'} hook 1234
{'name': 'emit signal', 'context': 'test'} hook 1234
"""


def test_dispatcher_alter_event_topics_while_dispatch(capsys):
    disp = EventDispatcher()
    evt = Event(name='emit signal', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.event.metadata, context.hook, data)
        if len(evt.topics) > 1:
            evt.topics.remove(t)

    evt.topics.append({'hook': [handler]}) 
    t = {'hook': [handler]}
    evt.topics.append(t)

    disp.dispatch(evt, 'hook', 1234)
    print('#2')
    disp.dispatch(evt, 'hook', 1234)
    captured = capsys.readouterr()
    assert captured.out == """\
{'name': 'emit signal', 'context': 'test'} hook 1234
{'name': 'emit signal', 'context': 'test'} hook 1234
#2
{'name': 'emit signal', 'context': 'test'} hook 1234
"""


def test_dispatcher_alter_event_topic_content_while_dispatch(capsys):
    disp = EventDispatcher()
    evt = Event(name='emit signal', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.event.metadata, context.hook, data)
        t['hook'].clear()

    evt.topics.append({'hook': [handler]}) 
    t = {'hook': [handler]}
    evt.topics.append(t)

    disp.dispatch(evt, 'hook', 1234)
    print('#2')
    disp.dispatch(evt, 'hook', 1234)
    captured = capsys.readouterr()
    assert captured.out == """\
{'name': 'emit signal', 'context': 'test'} hook 1234
{'name': 'emit signal', 'context': 'test'} hook 1234
#2
{'name': 'emit signal', 'context': 'test'} hook 1234
"""


def test_call_event_no_dispatcher(env, capsys):
    evt = Event()
    evt.enabled = True

    def process(env):
        print('schedule')
        yield evt(env.timeout(1))
        print('processed')

    env.process(process(env))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
schedule
processed
"""


def test_call_event_dispatcher_no_topic(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.enabled = True
    evt.dispatcher = EventDispatcher()
    event = env.timeout(1, 'main street')
    assert evt(event) is event
    env.run()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_event_dispatch_enable(capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()

    def handler(context, data):
        print(context.hook, context.event.metadata, data)

    evt.topics.append({
        'enable': [handler],
        'init': [handler],
    }) 

    evt.enabled = True
    evt.enabled = True  # check does not dispatch if no change
    evt.dispatch(hook='init', data='handle me')
    captured = capsys.readouterr()
    assert captured.out == """\
enable {'name': 'cross red light', 'context': 'test'} None
init {'name': 'cross red light', 'context': 'test'} handle me
"""


def test_event_dispatch_disable(capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        assert data is None
        print(context.hook, context.event.metadata, data)

    evt.topics.append({
        'disable': [handler],
        'init': [handler],
    }) 

    evt.enabled = False
    evt.enabled = False  # check does not dispatch if no change
    evt.dispatch(hook='init', data='handle me')
    captured = capsys.readouterr()
    assert captured.out == """\
disable {'name': 'cross red light', 'context': 'test'} None
"""


def test_event_dispatch_default_data(capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data)

    evt.topics.append({
        'init': [handler],
    }) 

    evt.dispatch(hook='init')
    captured = capsys.readouterr()
    assert captured.out == """\
init {'name': 'cross red light', 'context': 'test'} None
"""


def test_event_dispatch_no_dispatcher(capsys):
    evt = Event(name='cross red light', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    evt.topics.append({
        'init': [handler],
    }) 

    evt.dispatch(hook='init', data='handle me')
    captured = capsys.readouterr()
    assert captured.out == ""


def test_event_call_with_topics(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    evt.topics.append({
        'before': [handler, handler],
        'callbacks': [handler],
        'after': [handler],
    }) 
    evt.topics.append({
        'callbacks': [handler],
        'after': [handler, handler],
    }) 

    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
before {'name': 'cross red light', 'context': 'test'} main street
callbacks {'name': 'cross red light', 'context': 'test'} main street
callbacks {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
"""


def test_event_disable(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    evt.topics.append({
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }) 

    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_event_no_dispatcher_handlers(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    evt.topics.append({
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }) 

    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_call_event_reuse_simpyevent_preserve_order(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.enabled = True
    evt2 = Event(name='caught on camera', context='test')
    evt2.enabled = True
    dispatcher = EventDispatcher()
    evt.dispatcher = dispatcher
    evt2.dispatcher = dispatcher

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    evt.topics.append({
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }) 
    evt2.topics.append({
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }) 

    event = evt(env.timeout(1, 'main street'))
    evt2(event)
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
before {'name': 'caught on camera', 'context': 'test'} main street
callbacks {'name': 'cross red light', 'context': 'test'} main street
callbacks {'name': 'caught on camera', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'caught on camera', 'context': 'test'} main street
"""


def test_call_event_remove_handler_before_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }

    evt.topics.append(topic)
    evt(env.timeout(2, 'main street'))

    def process():
        yield env.timeout(1)
        topic['callbacks'].clear()

    env.process(process())
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
"""


# TODO : this is a consequence of the implementation,
#        is there any expected behaviour ?
def test_call_event_remove_handler_while_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def before(context, data):
        print(context.hook, context.event.metadata, data.value)
        topic['before'].pop()
        topic['callbacks'].pop()

    def callbacks(context, data):
        print(context.hook, context.event.metadata, data.value)

    def after(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [before, before],
        'callbacks': [callbacks, callbacks, callbacks],
        'after': [after],
    }

    evt.topics.append(topic)
    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
before {'name': 'cross red light', 'context': 'test'} main street
callbacks {'name': 'cross red light', 'context': 'test'} main street
after {'name': 'cross red light', 'context': 'test'} main street
"""


def test_call_event_disable_before_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }

    evt.topics.append(topic)
    evt(env.timeout(2, 'main street'))

    def process():
        yield env.timeout(1)
        evt.enabled = False

    env.process(process())
    env.run()
    captured = capsys.readouterr()
    assert captured.out == ""


# TODO : this is a consequence of the implementation,
#        is there any expected behaviour ?
def test_call_event_disable_while_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def before(context, data):
        print(context.hook, context.event.metadata, data.value)
        evt.enabled = False

    def callbacks(context, data):
        print(context.hook, context.event.metadata, data.value)

    def after(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [before, before],
        'callbacks': [callbacks],
        'after': [after],
    }

    evt.topics.append(topic)
    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
before {'name': 'cross red light', 'context': 'test'} main street
"""


def test_call_event_remove_dispatcher_before_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def handler(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [handler],
        'callbacks': [handler],
        'after': [handler],
    }

    evt.topics.append(topic)
    evt(env.timeout(2, 'main street'))

    def process():
        yield env.timeout(1)
        evt.dispatcher = None

    env.process(process())
    env.run()
    captured = capsys.readouterr()
    assert captured.out == ""


# TODO : this is a consequence of the implementation,
#        is there any expected behaviour ?
def test_call_event_remove_dispatcher_while_processed(env, capsys):
    evt = Event(name='cross red light', context='test')
    evt.dispatcher = EventDispatcher()
    evt.enabled = True

    def before(context, data):
        print(context.hook, context.event.metadata, data.value)
        evt.dispatcher = None

    def callbacks(context, data):
        print(context.hook, context.event.metadata, data.value)

    def after(context, data):
        print(context.hook, context.event.metadata, data.value)

    topic = {
        'before': [before, before],
        'callbacks': [callbacks],
        'after': [after],
    }

    evt.topics.append(topic)
    evt(env.timeout(1, 'main street'))
    env.run()
    captured = capsys.readouterr()
    assert captured.out == """\
before {'name': 'cross red light', 'context': 'test'} main street
before {'name': 'cross red light', 'context': 'test'} main street
"""
