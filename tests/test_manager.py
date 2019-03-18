#!/usr/bin/env python
import pytest
from simpy_events.manager import (Handlers, NameSpace, RootNameSpace,
                                  EventType, Topic, _hooks)
from simpy_events.event import EventDispatcher, Event
import simpy
import sys


@pytest.fixture
def env():
    yield simpy.Environment()


@pytest.fixture
def root():
    class Dispatcher(EventDispatcher):
        def dispatch(self, event, hook, data):
            metadata = {key: str(item) for key, item
                        in event.metadata.items()}
            try:
                # data is a simpy event
                print('dispatching', metadata, hook, data.value)
            except AttributeError:
                # data is something else
                print('dispatching', metadata, hook, data)
            super().dispatch(event, hook, data)

    return RootNameSpace(dispatcher=Dispatcher())


def test_handlers_add_handlers():
    lst = []
    handlers = Handlers(lst)
    assert len(handlers) == 0

    @handlers 
    def handler(*args, **kw):
        pass

    assert handlers[0] is handler
    assert lst == [handler]
    assert len(handlers) == 1
    assert list(handlers) == lst

    handlers.append(handler)
    assert len(handlers) == 2
    assert lst == [handler, handler]


def test_handlers_remove_handlers():

    def handler1(*args, **kw):
        pass

    def handler2(*args, **kw):
        pass

    lst = [handler1, handler2]
    handlers = Handlers(lst)
    assert len(handlers) == 2

    del handlers[0]
    assert len(handlers) == 1
    assert lst == [handler2]

    assert handlers.pop() is handler2
    assert len(handlers) == 0
    assert lst == []

    with pytest.raises(ValueError):
        handlers.remove(handler1)
    with pytest.raises(IndexError):
        del handlers[0]
    with pytest.raises(IndexError):
        handlers[0]


def test_handlers_replace_handlers():

    def handler1(*args, **kw):
        pass

    def handler2(*args, **kw):
        pass

    lst = [handler1, handler2]
    handlers = Handlers(lst)
    assert len(handlers) == 2

    handlers[0] = handler2
    assert len(handlers) == 2
    lst = [handler2, handler2]

    handlers[:] = [handler1, handler1]
    assert len(handlers) == 2
    lst = [handler1, handler1]


def test_namespace_root_properties(root):
    assert root.name is None
    assert root.path is None


def test_namespace_create(root):
    ns = root.ns('my ns')
    assert root.ns('my ns') is ns
    assert ns.name == 'my ns'
    assert ns.path == '::my ns'


def test_namespace_absolute_path(root):
    ns = root.ns('::my ns')
    assert root.ns('my ns') is ns
    assert ns.ns('::my ns') is ns
    assert ns.ns('my ns') is not ns
    assert ns.name == 'my ns'
    assert ns.path == '::my ns'


def test_namespace_sub_level(root):
    ns = root.ns('my ns')
    sub = ns.ns('sub level')
    assert sub.name == 'sub level'
    assert sub.path == '::my ns::sub level'
    assert sub is root.ns('my ns::sub level')
    assert sub is ns.ns('sub level')


def test_namespace_sub_level_depth(root):
    ns = root.ns('my ns')
    sub = ns.ns('sub level::sub level2')
    assert sub.name == 'sub level2'
    assert sub.path == '::my ns::sub level::sub level2'
    assert sub is root.ns('my ns::sub level::sub level2')
    assert sub is ns.ns('sub level::sub level2')
    assert sub is ns.ns('sub level').ns('sub level2')


def test_namespace_ignore_redundant_separator(root):
    assert root.ns('my ns::') is root.ns('my ns')
    assert root.ns('my ns::::') is root.ns('my ns')
    assert root.ns('::my ns') is root.ns('my ns')
    assert root.ns('::::my ns') is root.ns('my ns')
    assert root.ns('::my ns::') is root.ns('my ns')
    assert root.ns('::::my ns::::') is root.ns('my ns')


def test_namespace_colon_name(root):
    assert root.ns('my ns:') is not root.ns('my ns')
    assert root.ns('my ns:::') is root.ns('my ns').ns(':')


def test_namespace_ignore_redundant_separator_sub_levels(root):
    assert root.ns('my ns::sub::') is root.ns('my ns::sub')
    assert root.ns('my ns::::sub') is root.ns('my ns::sub')
    assert root.ns('my ns::sub::::') is root.ns('my ns::sub')
    assert root.ns('my ns::::sub::::') is root.ns('my ns::sub')
    assert root.ns('my ns::::sub1::::sub2') is root.ns('my ns::sub1::sub2')
    assert root.ns('my ns::::sub1::::sub2::') is root.ns('my ns::sub1::sub2')


def test_namespace_empty(root):
    with pytest.raises(ValueError):
        root.ns('')
    with pytest.raises(ValueError):
        root.ns('::')
    with pytest.raises(ValueError):
        root.ns('::::')


def test_create_event_type_empty(root):
    with pytest.raises(ValueError):
        et = root.event_type('')
    with pytest.raises(ValueError):
        et = root.event_type('my ns::')
    with pytest.raises(ValueError):
        et = root.event_type('::my ns::')
    with pytest.raises(ValueError):
        et = root.event_type('::my ns::sub::')


def test_create_event_type(root):
    et = root.event_type('my event')
    assert isinstance(et, EventType)
    assert et.name == 'my event'
    assert et.ns is root
    assert list(et.instances) == []
    assert list(et.topics) == []


def test_create_event_type_root_absolute_path(root):
    et = root.event_type('my event')
    assert et is root.event_type('::my event')


def test_create_event_type_sub_level(root):
    et = root.event_type('my app::sub1::my event')
    assert et.name == 'my event'
    ns1 = root.ns('my app') 
    ns2 = root.ns('my app::sub1') 
    assert ns2 is et.ns
    assert root.event_type('my app::sub1::my event') is et
    assert root.event_type('::my app::sub1::my event') is et
    assert ns2.event_type('my event') is et
    assert ns1.event_type('sub1::my event') is et


def test_event_type_create_event(root):
    et = root.event_type('my app::my event')

    evt = et.create()
    assert isinstance(evt, Event)
    assert list(et.instances) == [evt]
    evt2 = et.create()
    assert list(et.instances) == [evt, evt2]


def test_event_type_create_event_check_metadata(root):
    et = root.event_type('my app::my event')
    evt = et.create()
    assert evt.metadata == {
        'name': 'my event',
        'ns': root.ns('my app'),
    }


def test_event_type_create_event_with_metadata(root):
    et = root.event_type('my app::my event')
    evt = et.create(context='test')
    assert evt.metadata == {
        'name': 'my event',
        'ns': root.ns('my app'),
        'context': 'test',
    }
     

def test_event_type_create_event_override_metadata(root):
    et = root.event_type('my app::my event')
    evt = et.create(context='test', name='funky')
    assert evt.metadata == {
        'name': 'funky',
        'ns': root.ns('my app'),
        'context': 'test',
    }


@pytest.fixture
def dispatcher():
    class MyDispatcher:
        def __init__(self, name):
            self.name = name

        def dispatch(self, event, hook, data):
            metadata = {key: str(item) for key, item
                        in event.metadata.items()}
            print(self.name, ':', metadata, hook, data)

    return MyDispatcher


def test_dispatcher_property(root, capsys, dispatcher):
    root.dispatcher = dispatcher('root')
    ns = root.ns('my ns')
    sub = ns.ns('sub')
    et = root.event_type('my ns::sub::my event')
    et2 = root.event_type('my ns::sub::my event2')

    print('# create events')
    evt1 = et.create(id='E1')
    evt1.enabled = True
    evt2 = et.create(id='E2')
    evt2.enabled = True
    evt3 = et2.create(id='E3')
    evt3.enabled = True

    def dispatch():
        evt1.dispatch('test')
        evt2.dispatch('test')
        evt3.dispatch('test')

    print('# change root dispatcher')
    root.dispatcher = dispatcher('root2')
    dispatch()

    print('# set dispatcher on sub')
    sub.dispatcher = dispatcher('sub')
    dispatch()

    print('# set dispatcher on event type')
    et.dispatcher = dispatcher('my event')
    et2.dispatcher = dispatcher('my event2')
    dispatch()

    print('# set dispatcher on my ns')
    ns.dispatcher = dispatcher('my ns')
    dispatch()

    print('# remove dispatcher on sub')
    sub.dispatcher = None
    dispatch()

    print('# remove dispatcher on event type')
    et.dispatcher = None
    et2.dispatcher = None
    dispatch()

    print('# remove dispatcher on my ns')
    ns.dispatcher = None
    dispatch()

    captured = capsys.readouterr()
    print('test_dispatcher_property:\n', file=sys.stderr)
    print(captured.out, file=sys.stderr)
    assert captured.out == """\
# create events
root : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} enable None
root : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} enable None
root : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} enable None
# change root dispatcher
root2 : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
root2 : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
root2 : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# set dispatcher on sub
sub : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
sub : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
sub : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# set dispatcher on event type
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
my event2 : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# set dispatcher on my ns
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
my event2 : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# remove dispatcher on sub
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
my event : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
my event2 : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# remove dispatcher on event type
my ns : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
my ns : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
my ns : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# remove dispatcher on my ns
root2 : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
root2 : {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
root2 : {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
"""


def test_enabled_property(root, capsys):
    ns = root.ns('my ns')
    sub = ns.ns('sub')
    et = root.event_type('my ns::sub::my event')
    et2 = root.event_type('my ns::sub::my event2')

    print('# create events')
    evt1 = et.create(id='E1')
    evt2 = et.create(id='E2')
    evt3 = et2.create(id='E3')

    def dispatch():
        evt1.dispatch('test')
        evt2.dispatch('test')
        evt3.dispatch('test')

    print('# change root enabled')
    root.enabled = True
    dispatch()

    print('# set enabled on sub')
    sub.enabled = False
    dispatch()

    print('# set enabled on event type')
    et.enabled = True
    et2.enabled = True
    dispatch()

    print('# set enabled on my ns')
    ns.enabled = False 
    dispatch()

    print('# remove enabled on sub')
    sub.enabled = None
    dispatch()

    print('# remove enabled on event type')
    et.enabled = None
    et2.enabled = None
    dispatch()

    print('# remove enabled on my ns')
    ns.enabled = None
    dispatch()

    captured = capsys.readouterr()
    print('test_enabled_property:\n', file=sys.stderr)
    print(captured.out, file=sys.stderr)
    assert captured.out == """\
# create events
# change root enabled
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# set enabled on sub
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} disable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} disable None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} disable None
# set enabled on event type
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# set enabled on my ns
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# remove enabled on sub
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
# remove enabled on event type
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} disable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} disable None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} disable None
# remove enabled on my ns
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} enable None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E1'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event', 'id': 'E2'} test None
dispatching {'ns': '::my ns::sub', 'name': 'my event2', 'id': 'E3'} test None
"""


def test_ns_create_event_empty(root):
    with pytest.raises(ValueError):
        et = root.event('')
    with pytest.raises(ValueError):
        et = root.event('my ns::')
    with pytest.raises(ValueError):
        et = root.event('::my ns::')
    with pytest.raises(ValueError):
        et = root.event('::my ns::sub::')


def test_ns_create_event(root):
    evt = root.event('my app::my event')
    assert isinstance(evt, Event)
    et = root.event_type('my app::my event')
    assert list(et.instances) == [evt]


def test_ns_create_event_absolute_path(root):
    evt = root.event('::my app::my event')
    assert isinstance(evt, Event)
    et = root.event_type('my app::my event')
    assert list(et.instances) == [evt]


def test_ns_create_event_sub_levels(root):
    evt = root.event('my app::sub::my event')
    assert isinstance(evt, Event)
    et = root.event_type('my app::sub::my event')
    assert list(et.instances) == [evt]


def test_ns_create_event_in_root_absolute_path(root):
    evt = root.event('::my event')
    assert isinstance(evt, Event)
    et = root.event_type('my event')
    assert list(et.instances) == [evt]


def test_create_topic_empty(root):
    with pytest.raises(ValueError):
        root.topic('')
    with pytest.raises(ValueError):
        root.topic('my ns::')
    with pytest.raises(ValueError):
        root.topic('::my ns::')
    with pytest.raises(ValueError):
        root.topic('::my ns::sub::')


def test_create_topic(root):
    topic = root.topic('my topic')
    assert isinstance(topic, Topic)
    assert topic.name == 'my topic'
    assert topic.ns is root
    assert list(topic) == []


def test_create_topic_root_absolute_path(root):
    topic = root.topic('my topic')
    assert topic is root.topic('::my topic')


def test_create_topic_sub_level(root):
    topic = root.topic('my app::sub1::my topic')
    assert topic.name == 'my topic'
    ns1 = root.ns('my app') 
    ns2 = root.ns('my app::sub1') 
    assert ns2 is topic.ns
    assert root.topic('my app::sub1::my topic') is topic
    assert root.topic('::my app::sub1::my topic') is topic
    assert ns2.topic('my topic') is topic
    assert ns1.topic('sub1::my topic') is topic


def test_topic_add_events(root):
    topic = root.topic('my topic')
    assert len(topic) == 0

    topic.append('my event')
    assert len(topic) == 1
    assert 'my event' in topic
    
    topic.append('my event 2')
    assert len(topic) == 2
    assert 'my event 2' in topic

    assert list(topic) == ['my event', 'my event 2']


def test_topic_add_events_can_add_same(root):
    topic = root.topic('my topic')
    topic.append('my event')
    topic.append('my event')
    topic.append('my app::my event')
    topic.append('my app::my event')

    assert list(topic) == ['my event', 'my event',
                           'my app::my event', 'my app::my event']


def test_topic_add_events_preserve_items(root):
    topic = root.topic('my app::sub::my topic')
    topic.append('my event')
    topic.append('sub2::my event')
    topic.append('::my app::sub::my event2')
    topic.append('::my other app::my event')
    topic.append(':::::my other app::::sub:::my event')

    assert list(topic) == [
        'my event',
        'sub2::my event',
        '::my app::sub::my event2',
        '::my other app::my event',
        ':::::my other app::::sub:::my event',
    ]


def test_topic_remove_events(root):
    topic = root.topic('my topic')
    topic.append('my event')
    topic.append('my event 2')
    topic.append('my app::sub::my event')
    assert len(topic) == 3

    del topic[1]
    assert len(topic) == 2
    assert 'my event' in topic

    topic.remove('my event')
    assert len(topic) == 1

    topic.remove('my app::sub::my event')
    assert len(topic) == 0


def test_topic_remove_events_not_in_topic(root):
    topic = root.topic('my app::my topic')
    topic.append('my event')
    topic.append('my app::my event2')

    with pytest.raises(ValueError):
        topic.remove('my event 2')
    with pytest.raises(ValueError):
        topic.remove('my app::my event')
    with pytest.raises(ValueError):
        topic.remove('my event2')
    with pytest.raises(IndexError):
        del topic[2]


def test_topic_get_event_not_in_topic(root):
    topic = root.topic('my app::my topic')
    topic.append('my event')
    topic.append('my app::my event2')

    with pytest.raises(IndexError):
        topic[2]
    with pytest.raises(ValueError):
        topic.index('my other event')
    with pytest.raises(ValueError):
        topic.index('my app::my event')
    with pytest.raises(ValueError):
        topic.index('my event2')


def test_topic_get_use_slice(root):
    topic = root.topic('my topic')
    lst = [
        'my event',
        'my event 2',
        'my event 3',
        'my event 4',
    ]
    topic.extend(lst)

    assert topic[:] == lst
    assert topic[1:3] == ['my event 2', 'my event 3']


def test_topic_set_use_slice(root):
    topic = root.topic('my topic')
    lst = [
        'my event',
        'my event 2',
        'my event 3',
        'my event 4',
    ]

    with pytest.raises(NotImplementedError):
        topic[:] = lst

    assert len(topic) == 0


def test_topic_del_use_slice(root):
    topic = root.topic('my topic')
    lst = [
        'my event',
        'my event 2',
        'my event 3',
        'my event 4',
    ]
    topic.extend(lst)

    with pytest.raises(NotImplementedError):
        del topic[:]

    assert list(topic) == lst


def test_topic_set_invalid_index(root):
    topic = root.topic('my topic')
    lst = [
        'my event',
        'my event 2',
        'my event 3',
        'my event 4',
    ]
    topic.extend(lst)

    with pytest.raises(IndexError):
         topic[99] = 'my event 99'

    assert list(topic) == lst


def test_topic_replace_events(root):
    topic = root.topic('my topic')
    topic.append('my event')
    topic.append('my event 2')

    topic[1] = 'my event 3'
    assert list(topic) == ['my event', 'my event 3']


@pytest.fixture
def event_samples():
    def met(root, *event_types):
        """ creates an event type and two instances / event type for each """
        rv = []
        for evt in event_types:
            rv.append(root.event_type(evt))
            # create two Event instances for each event type
            root.event(evt)
            root.event(evt)
        return rv if len(rv) > 1 else rv[0]
        
    return met


def check_topic_in_events(topic, events, nbr=1):
    """ check topic is attached 'nbr' times to all event instances in events """
    topic = topic._topic
    for ev in events:
        found = 0
        for tp in ev.topics:
            if topic is tp:
                found += 1
        assert found == nbr, (f'{topic} (id: {id(topic)}) found {found} times '
                              f'in {ev}, expected {nbr} times; event topics: '
                              f'{ev.topics} (ids: {map(id, ev.topics)})')
        

def test_link_topic_and_events_add_events_same_ns(root,
                                                  event_samples):
    topic1 = root.topic('my app::my topic')
    topic2 = root.topic('my app::my topic2')
    et1, et2 = event_samples(root, 'my app::my event', 'my app::my event2')
    topic2.append('my event')
    topic1.append('my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic2, et1.instances)
    topic1.append('my event2')
    topic2.append('my event2')
    check_topic_in_events(topic1, et2.instances)
    check_topic_in_events(topic2, et2.instances)


def test_link_topic_and_events_add_events_with_ns(root,
                                                  event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2 = event_samples(root, 'my app::my event', 'my other app::my event')
    topic1.append('::my app::my event')
    topic1.append('::my other app::my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic1, et2.instances)


def test_link_topic_and_events_add_events_with_ns_sub_level(root,
                                                            event_samples):
    topic1 = root.topic('my app::my topic')
    topic2 = root.topic('my app::my topic2')
    topic3 = root.topic('my app::my topic3')
    et1, et2 = event_samples(root, 'my app::sub::my event', 'my other app::sub::my event')
    topic1.append('sub::my event')
    topic2.append('::my app::sub::my event')
    topic3.append('::my other app::sub::my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic2, et1.instances)
    check_topic_in_events(topic3, et2.instances)


def test_link_topic_and_events_add_events_before(root,
                                                 event_samples):
    topic1 = root.topic('my app::my topic')
    topic2 = root.topic('my app::my topic2')
    topic1.append('my event')
    topic1.append('::my app::my event2')
    topic2.append('my event')
    et1, et2 = event_samples(root, 'my app::my event', 'my app::my event2')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic2, et1.instances)
    check_topic_in_events(topic1, et2.instances)


def test_link_topic_and_events_add_events_X(root,
                                            event_samples):
    topic1 = root.topic('my app::my topic')
    et1 = event_samples(root, 'my app::my event')
    topic1.append('my event')
    topic1.append('::my app::my event')
    topic1.append('my event')
    topic1.append('::my app::my event')
    check_topic_in_events(topic1, et1.instances, 4)


def test_link_topic_and_events_remove_events_same_ns(root,
                                                     event_samples):
    topic1 = root.topic('my app::my topic')
    topic2 = root.topic('my app::my topic2')
    et1 = event_samples(root, 'my app::my event')
    topic1.append('my event')
    topic1.append('my event')
    topic2.append('my event')

    topic1.remove('my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic2, et1.instances)
    topic2.remove('my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic2, et1.instances, 0)
    topic1.remove('my event')
    check_topic_in_events(topic1, et1.instances, 0)


def test_link_topic_and_events_remove_events_with_ns(root,
                                                     event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2 = event_samples(root, 'my app::my event', 'my other app::my event')
    topic1.append('my event')
    topic1.append('::my app::my event')
    topic1.append('::my other app::my event')

    topic1.remove('::my app::my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic1, et2.instances)
    topic1.remove('my event')
    check_topic_in_events(topic1, et1.instances, 0)
    check_topic_in_events(topic1, et2.instances)
    topic1.remove('::my other app::my event')
    check_topic_in_events(topic1, et2.instances, 0)


def test_link_topic_and_events_remove_events_with_ns_sub_level(root,
                                                               event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2 = event_samples(root, 'my app::sub::my event', 'my other app::sub::my event')
    topic1.append('sub::my event')
    topic1.append('::my app::sub::my event')
    topic1.append('::my other app::sub::my event')

    topic1.remove('sub::my event')
    check_topic_in_events(topic1, et1.instances)
    check_topic_in_events(topic1, et2.instances)
    topic1.remove('::my app::sub::my event')
    check_topic_in_events(topic1, et1.instances, 0)
    check_topic_in_events(topic1, et2.instances)
    topic1.remove('::my other app::sub::my event')
    check_topic_in_events(topic1, et2.instances, 0)


def test_link_topic_and_events_replace_events_same_ns(root,
                                                      event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2, et3 = event_samples(root, 
                                  'my app::my event',
                                  'my app::my event2',
                                  'my app::my event3')
    lst = [
        'my event',
        'my event2',
        'my event3',
    ]
    topic1.extend(lst)

    topic1[1] = 'my event3'
    check_topic_in_events(topic1, et1.instances, 1)
    check_topic_in_events(topic1, et2.instances, 0)
    check_topic_in_events(topic1, et3.instances, 2)


def test_link_topic_and_events_replace_events_with_ns(root,
                                                      event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2 = event_samples(root, 
                                  'my app::my event',
                                  'my other app::my event')
    lst = [
        'my event',
        '::my app::my event',
        '::my other app::my event',
    ]
    topic1.extend(lst)

    topic1[0] = '::my other app::my event'
    check_topic_in_events(topic1, et1.instances, 1)
    check_topic_in_events(topic1, et2.instances, 2)


def test_link_topic_and_events_replace_events_with_ns_sub_level(root,
                                                                event_samples):
    topic1 = root.topic('my app::my topic')
    et1, et2, et3 = event_samples(root, 
                                  'my app::sub::my event',
                                  'my app::sub::my event2',
                                  'my app::sub::my event3')
    lst = [
        'sub::my event',
        'sub::my event2',
        '::my app::sub::my event3',
    ]
    topic1.extend(lst)

    topic1[1] = 'sub::my event3'
    topic1[2] = '::my app::sub::my event'
    check_topic_in_events(topic1, et1.instances, 2)
    check_topic_in_events(topic1, et2.instances, 0)
    check_topic_in_events(topic1, et3.instances, 1)


def test_topic_handlers(root):
    topic = root.topic('my app::my topic')
    handlers = topic.handlers('before') 
    assert isinstance(handlers, Handlers)
    assert topic.handlers('before') is handlers
    assert topic.handlers('after') is not handlers


def test_topic_get_handlers(root):
    topic = root.topic('my app::my topic')
    assert topic.get_handlers('before') is None
    handlers = topic.handlers('before') 
    assert topic.get_handlers('before') is handlers


@pytest.fixture
def hooks():
    return _hooks


def test_topic_hooks_property(root, hooks):
    topic = root.topic('my app::my topic')
    for hook in hooks:
        assert getattr(topic, hook) is topic.handlers(hook)


def test_event_type_create_event_enabled_dispatched_topics(root, capsys):
    """ check topics are already linked to the event when 'enable' is
        dispatched when creating the event and the event is enabled.
    """
    topic = root.topic('my app::topic')
    topic.append('my event')
    root.event_type('my app::my event').enabled = True

    @topic.enable
    def on_enable(context, data):
        print('on_enable:', context.hook, context.event.metadata['name'])

    root.event('my app::my event')
    captured = capsys.readouterr()
    assert captured.out == """\
dispatching {'ns': '::my app', 'name': 'my event'} enable None
on_enable: enable my event
"""


def test_ns_handlers(root):
    ns = root.ns('my ns')
    topic = ns.topic('my topic')
    handlers = topic.handlers('before') 
    assert ns.handlers('my topic', 'before') is handlers


def test_ns_handlers_other_ns(root):
    ns = root.ns('my ns')
    topic = root.topic('my other ns::my topic')
    handlers = topic.handlers('before') 
    assert ns.handlers('::my other ns::my topic', 'before') is handlers


def test_ns_hooks_property(root, hooks):
    ns = root.ns('my ns')
    topic = root.topic('my ns::my topic')
    for hook in hooks:
        assert getattr(ns, hook)('my topic') is topic.handlers(hook)


def test_ns_hooks_property_other_ns(root, hooks):
    ns = root.ns('my ns')
    topic = root.topic('my other ns::my topic')
    for hook in hooks:
        assert (getattr(ns, hook)('::my other ns::my topic')
                is topic.handlers(hook))
