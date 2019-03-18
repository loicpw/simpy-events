#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .event import Event, EventDispatcher
import collections
from functools import partial


class Handlers(collections.MutableSequence):
    """ Holds a sequence of handlers.

        `Handlers` is a sequence object which holds handlers for a
        specific hook in a topic.

        .. seealso:: `simpy_events.event.Event`

        `Handlers` behave like a `list` expect it's also callable so it
        can be used as a decorator to append handlers to it.
    """
    def __init__(self, lst=None):
            self._lst = [] if lst is None else lst

    def __getitem__(self, index):
        return self._lst[index]

    def __setitem__(self, index, value):
        self._lst[index] = value

    def __delitem__(self, index):
        del self._lst[index]

    def __len__(self):
        return len(self._lst)

    def insert(self, index, value):
        self._lst.insert(index, value)

    def __call__(self, fct):
        """ append `fct` to the sequence.

            `Handlers` object can be used as a decorator to append a
            handler to it.
        """
        self.append(fct)
        return fct


class Topic(collections.MutableSequence):
    """ Holds a mapping of handlers to link to specific events.

        `Topic` is a sequence that contains names of events to be linked
        automatically when they are created or the name of existing
        events is added.

        When events are created they're registered by event type
        (`EventType`), identified by a name. If that name is contained
        in a `Topic` then the topic will be added to the
        `simpy_events.event.Event`'s `topcis` sequence and the handlers
        it contains will be called when the event is dispatched.

        a `Topic` carries a `dict` containing sequences of handlers for
        specific hooks ('before', 'after'...), and this `dict` is added
        to `simpy_events.event.Event`'s topics. The topic's dict is
        added to an event's topics sequence either when the
        `simpy_events.event.Event` is created or when the corresponding
        event's type (name) is added to the `Topic`.

        `Topic`'s `dict` contains key:value pairs where keys are hook
        names ('before', 'after'...) and values are `Handlers` objects.
        The handler functions added to the `Topic` are added to the
        `Handlers` objects.

        The topic is removed automatically from an
        `simpy_events.event.Event` if the corresponding event type
        (name) is removed from the `Topic`.

        .. seealso:: `simpy_events.event.Event`, `NameSpace.topic`,
            `NameSpace.event`
    """
    def __init__(self, ns, name):
        """ initializes a `Topic` attached to `ns` by its name `name`.

            .. seealso:: `Topic` are expected to be initialized
                automatically, see also `NameSpace.topic`.

            `ns` is the `NameSpace` instance that created and holds the
            `Topic`.

            `name` is the name of the `Topic` and under which it's
            identified in its parent `ns`.
        """
        self._ns = ns
        self._name = name
        self._events = []
        self._topic = {}

    @property
    def topic(self):
        """ (read only) The `dict` that is added to event's `topics` """
        return self._topic

    @property
    def ns(self):
        """ (read only) The `NameSpace` that holds the `Topic` """
        return self._ns

    @property
    def name(self):
        """ (read only) The name of the `Topic` """
        return self._name

    def __getitem__(self, index):
        """ return an event name added to the `Topic` """
        return self._events[index]

    def __setitem__(self, index, event):
        """ add an event name to the `Topic`

            this will take care of removing the topic from the events
            identified by the current event name at the specified
            `index`

            then the new event name will be added to the sequence and
            the corresponding events will be linked if instances
            exist.

            .. note:: cannot use a `slice` as `index`, this will raise
                a `NotImplementedError`.
        """
        if isinstance(index, slice):
            raise NotImplementedError('slice is not supported, only integer')

        # remove current
        self._remove(self._events[index])
        # add new
        self._events[index] = event
        self._add(event)

    def _add(self, event):
        et = self._ns.event_type(event)
        et.add_topic(self._topic)

    def _remove(self, event):
        et = self._ns.event_type(event)
        et.remove_topic(self._topic)

    def __delitem__(self, index):
        """ remove an event name from the `Topic`

            this will remove the topic from the events identified by the
            event name at the removed `index`.

            .. note:: cannot use a `slice` as `index`, this will raise
                a `NotImplementedError`.
        """
        if isinstance(index, slice):
            raise NotImplementedError('slice is not supported, only integer')

        self._remove(self._events[index])
        del self._events[index]

    def __len__(self):
        return len(self._events)

    def insert(self, index, event):
        """ insert an event name into the `Topic`

            The new event name is added to the sequence at the specified
            `index` and the corresponding events are linked if instances
            exist.
        """
        self._events.insert(index, event)
        self._add(event)

    def get_handlers(self, hook):
        """ eq. to `Topic.handlers` but doesnt create the `Handlers`

            return the `Handlers` sequence or `None`.
        """
        return self._topic.get(hook)

    def handlers(self, hook):
        """ return the `Handlers` sequence for the hook `hook`.

            the `Handlers` sequence for a given hook (i.e 'before',
            'after'...) is created in a lazy way by the `Topic`.

            .. seealso:: `simpy_events.event.Event` for details about
                hooks.

            Since `Handlers` can be used as a decorator itself to add a
            handler to it, this method can be used as a decorator to
            register a handler, for ex ::

                @topic.handlers('before')
                def handler(context, data):
                    pass

            .. seealso::
                + `Topic.get_handlers`
                + `Topic.enable`
                + `Topic.disable`
                + `Topic.before`
                + `Topic.callbacks`
                + `Topic.after`
        """
        try:
            return self._topic[hook]
        except KeyError:
            handlers = Handlers()
            self._topic[hook] = handlers
            return handlers


# add a convenience registering method for each known hook
# created properties simply return a `partial` method using
# `Topic.handlers`
_hooks = (
    'before',
    'callbacks',
    'after',
    'enable',
    'disable',
)

for _ in _hooks:
    @property
    def p(self, hook=_):
        f"(read only) equivalent to `Topic.handlers`('{_}')"
        return self.handlers(hook)

    setattr(Topic, _, p)


class EventsProperty:
    """ Set an attribue value for a hierarchy of parents/children

        `EventsProperty` is used internally to automatically set the
        value of a specific attribute from a parent down to a
        hierarchy given the following rules:

        + the value of the parent is set recursively to children until
          a child contains a not `None` value.

        + if the value of a given node is set to `None` then the first
          parent whose value is not `None` will be used to replace the
          value recursively.

        In other words `EventsProperty` ensures the a hierarchically set
        value that can be overriden by children nodes.

        .. seealso:: `EventsPropertiesMixin`
    """
    def __init__(self, name, value, parent):
        """ creates a new hierarchical attribute linked to `parent`

            for each event added to this node its `name` attribute will
            be set every time the applicable value is updated (this
            `EventsProperty`'s value or a parent value depending on
            whether the value is `None` or not).
        """
        self.parent = parent
        if parent is not None:
            parent.children.append(self)
        self.children = []
        self._name = name
        self._events = []
        self._value = value

    @property
    def value(self):
        """ return the current value of this node in the hierarchy """
        return self._value

    @value.setter
    def value(self, value):
        """ set the value for this node in the hierarchy

            if `value` is `None` then the first value that is not `None`
            up in the hierarchy will be used to set the attribute of
            the events of this node and all the children whose value is
            `None` recursively down the hierarchy.

            if `value` is not `None` then all the events attached to
            this particular node and the events of all the children
            whose value is `None` recursively down the hierarchy will
            be updated.
        """
        self._value = value
        if value is None:
            assert self.parent is not None, 'value cannot be None'
            value = self._get_value()
        self._propagate(value)

    def _get_value(self):
        # get the first not `None` value in parents
        if self._value is None:
            parent = self
            while(parent._value) is None:
                parent = parent.parent
            return parent._value
        return self._value

    def _propagate(self, value):
        # set value on the events of this node
        self._set_value(value, self._events)
        # forward `value` down to the hierarchy
        children = self.children
        for child in children:
            if child.value is None:
                child._propagate(value)

    def _set_value(self, value, events):
        # set the attribute value to `value` for each event in `events`
        name = self._name
        for event in events:
            setattr(event, name, value)

    def add_event(self, event):
        """ add an event to this node

            the corresponding attribute will be hierarchically set
            starting from this node in the hierarchy for the added
            event.
        """
        self._events.append(event)
        self._set_value(self._get_value(), (event,))

    def remove_event(self, event):
        """ remove an event from the hierarchy.

            This doesn't modify the corresponding attribute.
        """
        self._events.remove(event)
        # TODO ==> value ?


class EventsPropertiesMixin:
    """ Internally used mixin class to add `EventsProperty` instances

        This class add an `EventsProperty` instance for each attribute
        name in `EventsPropertiesMixin._props` :

        + "dispatcher"
        + "enabled"

        This is used to ensure a hierarchically set value for the
        corresponding attribute of `simpy_events.event.Event` instances.

        .. seealso:: `NameSpace`, `EventType`

        For each attribute:

        + a `property` is used to set / get the value

        + the `EventsProperty` object is stored in a private attribute
          using the name '_{attr_name}' (ex: "_dispatcher")

        Then the `EventsPropertiesMixin._add_event_properties` and
        `EventsPropertiesMixin.remove_event_properties` methods can be
        used in subclasses to add / remove an event to / from the
        `EventsProperty` instances.
    """
    _props = (
        'dispatcher',
        'enabled',
    )

    def __init__(self, parent, **values):
        """ `parent` is either `None` or a `EventsPropertiesMixin`.

            `values` are optional extra keyword args to initialize the
            value of the `EventsProperty` objects (ex: dispatcher=...).

            For each managed attribute, the `EventsProperty` object is
            stored in a private attribute using the name '_{attr_name}'
            (ex: "_dispatcher").
        """

        for name in self._props:
            setattr(self, f'_{name}', EventsProperty(
                name,
                values.get(name),
                None if parent is None else getattr(parent, f'_{name}')
            ))

    def _add_event_properties(self, event):
        """ used in subclasses to add a `simpy_events.event.Event`.

            This add the event to each contained `EventsProperty` object,
            so the corresponding attribute is hierarchically set for the
            event.
        """
        for name in self._props:
            getattr(self, f'_{name}').add_event(event)

    def _remove_event_properties(self, event):
        """ used in subclasses to remove a `simpy_events.event.Event`.

            This remove the event from each contained `EventsProperty`
            object.
        """
        for name in self._props:
            getattr(self, f'_{name}').remove_event(event)


# create getter and setter for each property in EventsPropertiesMixin
for _ in EventsPropertiesMixin._props:
    @property
    def p(self, name=_):
        return getattr(self, f'_{name}').value

    @p.setter
    def p(self, value, name=_):
        getattr(self, f'_{name}').value = value

    setattr(EventsPropertiesMixin, _, p)


class EventType(EventsPropertiesMixin):
    """ Link a set of `simpy_events.event.Event` instances to a name.

        `EventType` allows to define an *event type* identified by
        a name in a given `NameSpace`, and create
        `simpy_events.event.Event` instances from it, which will allow
        to manage those instances as a group and share common
        properties:

        + `Topic` objects can be added to the `EventType` and
          then automatically linked to the `simpy_events.event.Event`
          instances.

        + the `simpy_events.event.Event` instances are managed through
          the `NameSpace`/`EventType` hierarchy that allows to manage
          the `simpy_events.event.Event.dispatcher` and
          `simpy_events.event.Event.enabled` values either for a given
          `NameSpace` or a given `EventType`.

        + the `NameSpace` instance and the name of the `EventType` will
          be given as metadata to the created events (see
          `EventType.create`).

        .. todo:: remove event instance ?
    """
    def __init__(self, ns, name):
        """ initializes an `EventType` attached to `ns` by name `name`.

            .. seealso:: `EventType` are expected to be initialized
                automatically, see also `NameSpace.event_type`.

            `ns` is the `NameSpace` instance that created and holds the
            `EventType`.

            `name` is the name of the `EventType` and under which it's
            identified in its parent `ns`.
        """
        super().__init__(parent=ns)
        self._metadata = {
            'ns': ns,
            'name': name,
        }
        self._name = name
        self._ns = ns
        self._instances = []
        self._topics = []

    @property
    def name(self):
        """ (read only) The name of the `EventType` """
        return self._name

    @property
    def ns(self):
        """ (read only) The `NameSpace` that holds the `EventType` """
        return self._ns

    @property
    def instances(self):
        """ iter on created `simpy_events.event.Event` instances """
        return iter(self._instances)

    @property
    def topics(self):
        """ iter on added `Topic` objects """
        return iter(self._topics)

    def create(self, **metadata):
        """ create a `simpy_events.event.Event` instance

            `metadata` are optional keyword args that will be forwarded
            as it is to initialize the event.

            by default two keyword args are given to the
            `simpy_events.event.Event` class:

            + `ns`: the `NameSpace` instance (`EventType.ns`)
            + `name`: the name of the `EventType` (`EventType.name`)

            those values will be overriden by custom values if
            corresponding keyword are contained in `metadata`.

            Once the event has been created the `Topic` objects linked
            to the `EventType` are linked to the
            `simpy_events.event.Event` instance.

            Then `simpy_events.event.Event.enabled` and
            `simpy_events.event.Event.dispatcher` values for the created
            event are synchronized with the hierarchy (`NameSpace`/
            `EventType`).
        """
        # create event
        kw = self._metadata.copy()
        kw.update(metadata)
        event = Event(**kw)
        self._instances.append(event)

        # link topics
        event.topics.extend(self._topics)

        # synchronize dispatcher and enabled properties
        self._add_event_properties(event)

        return event

    def add_topic(self, topic):
        """ add a `Topic` object to this `EventType`.

            This will immediately link the `Topic` to the existing and
            future created `simpy_events.event.Event` instances for this
            `EventType`,
        """
        self._topics.append(topic)
        for evt in self._instances:
            evt.topics.append(topic)

    def remove_topic(self, topic):
        """ remove a `Topic` object from this `EventType`.

            The `Topic` will immediately be unlinked from the existing
            `simpy_events.event.Event` instances for this `EventType`.
        """
        # since topics are dict we must check the id to remove the
        # correct instance ({} == {} is True)
        for i, tp in enumerate(self._topics):
            if tp is topic:
                del self._topics[i]
                break

        for evt in self._instances:
            topics = evt.topics
            for i, tp in enumerate(topics):
                if tp is topic:
                    del topics[i]
                    break


class NameSpace(EventsPropertiesMixin):
    """ Define a hierarchical name space to link events and handlers.

        `NameSpace` provides a central node to automatically link
        `simpy_events.event.Event` objects and their handlers.

        `NameSpace` allows to define `EventType` objects and create
        `simpy_events.event.Event` instances associated with those
        event types.

        It also allows to define `Topic` objects and link them to event
        types. Handlers can then be attached to the `Topic` objects,
        which will automatically link them to the related
        `simpy_events.event.Event` instances.

        Then, `NameSpace` and `EventType` also allow to set / override
        `simpy_events.event.Event.enabled` and
        `simpy_events.event.Event.dispatcher` attributes at a given
        point in the hierarchy.

        .. seealso:: `RootNameSpace`
    """
    separator = '::'

    def __init__(self, parent, name, root, **kwargs):
        """ `NameSpace` are expected to be initialized automatically

            .. seealso:: `NameSpace.ns`, `RootNameSpace`

            + `parent` is the parent `NameSpace` that created it
            + `name` is the name of the `NameSpace`
            + `root` is the `RootNameSpace` for the hierarchy
            + additional `kwargs` are forwarded to
              `EventsPropertiesMixin`
        """
        super().__init__(parent=parent, **kwargs)
        self._root = root
        self._name = name
        self._parent = parent
        self._events = {}
        self._topics = {}
        self._children = {}

    @property
    def name(self):
        """ (read only) the name of the `NameSpace`

            example::

                root = RootNameSpace(dispatcher)
                ns = root.ns('first::second::third')
                assert ns.name == 'third'
        """
        return self._name

    @property
    def path(self):
        """ (read only) return the absolute path of in the hierarchy

            example::

                root = RootNameSpace(dispatcher)
                ns = root.ns('first::second::third')
                assert ns.path == '::first::second::third'

            .. note:: **str(ns)** will return **ns.path**
        """
        parent = self._parent
        if parent is self._root:
            return f'{self.separator}{self._name}'
        return f'{parent.path}{self.separator}{self._name}'

    def __str__(self):
        """ return `NameSpace.path` """
        return self.path

    def ns(self, name):
        """ return or create the child `NameSpace` for `name`

            There is a unique `name`:`NameSpace` pair from a given
            `NameSpace` instance. It's automatically created when
            accessing it if it doesn't exist.

            `name` is either a relative or absolute name. An absolute
            name begins with '::'.

            If `name` is absolute the `NameSpace` is referenced from
            the `RootNameSpace` in the hierarchy, ex::

                ns = root.ns('one')
                assert ns.ns('::one::two') is root.ns('one::two')

            On the other hand a relative name references a `NameSpace`
            from the node on which ns is called, ex::

                ns = root.ns('one')
                assert ns.ns('one::two') is not root.ns('one::two')
                assert ns.ns('one::two') is ns.ns('one').ns('two')
                assert ns.ns('one::two') is root.ns('one::one::two')

            .. note:: `name` cannnot be empty (`ValueError`), and
                redundant separators ('::'), as well as trailing
                separators will be ignored, ex::

                    ns1 = ns.ns('::::one::::two::::::::three::')
                    assert ns1 is ns.ns('::one::two::three')

            .. note:: ':' will be processed as a normal character,
                ex::

                    assert ns.ns(':one').name == ':one'
                    ns1 = ns.ns(':one::two:::::three:')
                    ns2 = ns.ns(':one').ns('two').ns(':').ns('three:')
                    assert ns1 is ns2

            .. seealso:: `NameSpace.path`
        """
        sp = self.separator

        # query root if is absolute
        if name.startswith(sp):
            return self._root.ns(name[len(sp):])

        # ignore heading, trailing and repeated separators and
        # turn name into a sequence, for ex: '::::a::::::b::::c::d:::::'
        # will turns to 'a', 'b', 'c', 'd', ':'
        itername = iter(filter(None, name.split(sp)))

        # find / create the NameSpace instance in the hierarchy
        ns = self
        for _name in itername:
            # find or create child and forward if sub names
            try:
                child = ns._children[_name]
            except KeyError:
                child = NameSpace(parent=ns, name=_name, root=self._root)
                ns._children[_name] = child
            ns = child

        if ns is self:
            raise ValueError('name cannot be empty')
        return ns

    def _split_parent(self, name):
        # extract (NameSpace, <child name>) from `name`, where
        # `name` is expected to follow one of these patterns:
        # + '<ns path name>::<child name>'
        # + '<child name>'
        sp = self.separator

        if sp in name:
            ns, name = name.rsplit(sp, maxsplit=1)
            # return root if name == '::<name>'
            return (self.ns(ns), name) if ns else (self._root, name)
        # no ns specified in `name`
        return self, name

    def _get_object(self, name, mapping, obj_type):
        # find or create the object identified by the key `name`
        # in the mapping `mapping`. Uses `obj_type` to create
        # the object if it doesn't exist, in this case `obj_type` is
        # called with the following arguments:
        # + `self`: the `NameSpace` instance
        # + `name`
        # a `ValueError` is raised if `name` is empty
        if not name:
            raise ValueError('name cannot be empty')

        # find or create obj in the specified mapping
        try:
            obj = mapping[name]
        except KeyError:
            obj = obj_type(self, name)
            mapping[name] = obj
        return obj

    def event_type(self, name):
        """ find or create an `EventType`

            `name` is either relative or absolute (see `NameSpace.ns`
            for details).

            .. note:: the `EventType` objects have their own mapping
                within a given `NameSpace`, this means an `EventType`
                and a child `NameSpace` can have the same name, ex::

                    ns.event_type('domain')
                    ns.ns('domain')

            will create the `EventType` instance if it doesn't exist.
        """
        ns, name = self._split_parent(name)
        return ns._get_object(name, ns._events, EventType)

    def topic(self, name):
        """ find or create an `Topic`

            `name` is either relative or absolute (see `NameSpace.ns`
            for details).

            .. note:: the `Topic` objects have their own mapping
                within a given `NameSpace`, this means an `Topic`
                and a child `NameSpace` can have the same name, ex::

                    ns.topic('domain')
                    ns.ns('domain')

            will create the `Topic` instance if it doesn't exist.
        """
        ns, name = self._split_parent(name)
        return ns._get_object(name, ns._topics, Topic)

    def event(self, name, *args, **kwargs):
        """ create a `simpy_events.event.Event` instance

            `name` is the name of the event type to use, it is either
            relative or absolute (see `NameSpace.event_type`).

            additional `args` and `kwargs` are forwarded to
            `EventType.create`.

            `NameSpace.event` is a convenience method, the following ::

                ns.event('my event')

            is equivalent to ::

                ns.event_type('my event').create()

        """
        return self.event_type(name).create(*args, **kwargs)

    def handlers(self, name, hook):
        """ return the handlers for the topic `name` and the hook `hook`

            This is a convenience method that returns the `Handlers`
            sequence for a given `hook` in a given `Topic`.

            .. seealso:: `NameSpace.topic`, `Topic.handlers`

            Then the following ::

                ns.handlers('my topic', 'before')

            is equivalent to ::

                ns.topic('my topic').handlers('before')

            .. note:: this method can be used as a decorator to
                register a handler, for ex ::

                    @ns.handlers('my topic', 'before')
                    def handler(context, data):
                        pass
        """
        return self.topic(name).handlers(hook)


# add a convenience registering method for each known hook
# a property is added to NameSpace for each hook, which returns
# a partial method using NameSpace.handlers
for _ in _hooks:
    @property
    def p(self, hook=_):
        f"""(read only) equivalent to `NameSpace.handlers` with hook='{_}' ::

                NameSpace.{_}('my topic')

            is equivalent to ::

                NameSpace.handlers('my topic', {_})
        """
        return partial(self.handlers, hook=hook)

    setattr(NameSpace, _, p)


class RootNameSpace(NameSpace):
    """ The root `NameSpace` object in the hierarchy.

        the `RootNameSpace` differs from `NameSpace` because it has no
        parent, as a consequence:

        + `RootNameSpace.path` returns `None`

        + `RootNameSpace.name` returns `None`

        + `RootNameSpace.dispatcher` cannot be `None` (i.e unspecified)

          a value can be specified when creating the instance, otherwise
          a `simpy_events.event.EventDispatcher` will be created

        + `RootNameSpace.enabled` cannot be `None` (i.e unspecified)

          the value can be specifiied at creation (`False` by default)
    """
    def __init__(self, dispatcher=None, enabled=False):
        """ init the root `NameSpace` in the hierarchy

            + `dispatcher`: used (unless overriden in children) to set
                `simpy_events.event.Event.dispatcher`

              if the value is not provided then a
              `simpy_events.event.EventDispatcher` is created

            + `enabled`: used (unless overriden in children) to set
                `simpy_events.event.Event.enabled`

              Default value is `False`
        """
        if dispatcher is None:
            dispatcher = EventDispatcher()
        super().__init__(root=self, parent=None, name=None,
                         dispatcher=dispatcher, enabled=enabled)

    @NameSpace.path.getter
    def path(self):
        return None
