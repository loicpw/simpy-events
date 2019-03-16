#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
from itertools import chain


class Context:
    """ context object forwarded to event handlers by `EventDispatcher`

        contains following attributes:

        + `event`, the `Event` instance
        + `hook`, the name of the hook
    """
    def __init__(self, **attributes):
        """ initializes a new `Context` with keyword arguments

            creates an attribute for each provided keyword arg.
         """
        self.__dict__.update(attributes)


class EventDispatcher:
    """ Responsible for dispatching an event to `Event`'s handlers

        uses the `Event`'s sequence of `topics` to get all handlers for
        a given `hook` and call them sequentially.
    """
    def dispatch(self, event, hook, data):
        """ dispatch the event to each topic in `Event.topics`.

            args:

            + `event`, the `Event` instance
            + `hook`, the name of the hook to dispatch
            + `data`, data associated to the event

            .. seealso:: `Event.dispatch`

            Each `topic` is expected to be a mapping containing
            a sequence of handlers for a given `hook`. The `topic`
            will be ignored if it doesn't contain the `hook` key.

            For each sequence of handlers found for `hook`, a `tuple` is
            created to ensure consistency while iterating (it's likely
            handlers are removed / added while dispatching).

            Handlers are then called sequentially with the following
            arguments:

            + `context`, a `Context` object
            + `data`
        """
        context = Context(
            event=event,
            hook=hook,
        )
        for topic in [tuple(topic.get(hook, ())) for topic in event.topics]:
            for hdlr in topic:
                hdlr(context, data)


class Callbacks(collections.MutableSequence):
    """ Replace the 'callbacks' list in `simpy.events.Event` objects.

        Internally used to replace the single list of callbacks in
        `simpy.events.Event` objects.

        .. seealso:: `Event`

        It allows to add the `Event`'s hooks before, when
        and after the `simpy.events.Event` object is processed by
        `simpy` (that is when the items from its "callbacks" list are
        called).

        `Callbacks` is intended to replace the original `callbacks` list
        of the `simpy.events.Event` object When iterated, it chains the
        functions attached to `before`, `callbacks` and `after`.

        In order to behave as expected by `simpy`, adding or removing
        items from a `Callbacks` object works as expected by `simpy`:
        `Callbacks` is a `collections.MutableSequence` and callables
        added or removed from it will be called by `simpy` as regular
        callbacks, i.e *f(event)* where *event* is a
        `simpy.events.Event` object.

        When used to replace the `simpy.events.Event`'s callbacks
        attribute, it ensures the correct order is maintained if the
        original `simpy.events.Event`'s callbacks attribute was itself a
        `Callbacks` object, example: ::

            cross_red_light = Event(name='cross red light')
            get_caught = Event(name='caught on camera')
            evt = cross_red_light(env.timeout(1))
            yield get_caught(evt)

        In this example, the call order will be as follows ::

            - cross_red_light's before
            - get_caught's before
            - cross_red_light's callbacks
            - get_caught's callbacks
            - cross_red_light's after
            - get_caught's after
    """
    def __init__(self, event, before, callbacks, after):
        """ Attach the `Callbacks` obj to a `simpy.events.Event` obj.

            `event` is the `simpy.events.Event` object whose `callbacks`
            attribute is going to be replaced by this `Callbacks` object.

            `before`, `callbacks` and `after` are callables which will
            be called respectively before, when and after the `event` is
            actually processed by `simpy`.

            .. note:: the current `event.callbacks` attribute may
                already be a `Callbacks` object, see `Callbacks`
                description for details.
        """
        if isinstance(event.callbacks, Callbacks):
            cbks = event.callbacks
            self.callbacks = cbks.callbacks
            self.before = cbks.before
            self.after = cbks.after
        else:
            self.callbacks = event.callbacks
            self.before = []
            self.after = []

        self.before.append(before)
        self.after.append(after)
        self.callbacks.append(callbacks)

    def __getitem__(self, index):
        """ return callable item from 'callbacks' list """
        return self.callbacks[index]

    def __setitem__(self, index, value):
        """ set callable item in 'callbacks' list """
        self.callbacks[index] = value

    def __delitem__(self, index):
        """ del callable item from 'callbacks' list """
        del self.callbacks[index]

    def __len__(self):
        """ return number of callable items in 'callbacks' list """
        return len(self.callbacks)

    def insert(self, index, value):
        """ insert callable item in 'callbacks' list """
        self.callbacks.insert(index, value)

    def __iter__(self):
        """ return an iterator chaining the lists of callbacks:

            - 'before'
            - 'callbacks'
            - 'after'
        """
        return iter(chain(self.before, self.callbacks, self.after))


class Event:
    """ `Event` provides a node to access the event system.

        an `Event` is an endpoint that allows to dispatch a `hook` to a
        set of handlers. A `hook` identifies a particular state for the
        `Event`, note `Event` is intended to be used to *wrapp*
        `simpy.events.Event` objects.

        + **enable**: triggered when `Event.enabled` is set to `True`

        + **disable**: triggered when `Event.enabled` is set to to `False`

        + **before**: just before the `simpy.events.Event` is processed
          by `simpy`

        + **callbacks**: when the `simpy.events.Event` is processed by
          `simpy` (i.e when callbacks are called)

        + **after**: just after the `simpy.events.Event` is processed
          by `simpy`

        `Event` provides two options to dispatch an event through the
        event system:

        + immediately dispatch a `hook` with `Event.dispatch`: although
          this method is used internally it may be used to dispatch any
          arbitrary `hook` immediately.

        + call the `Event` providing a `simpy.events.Event` object, so
          the 'before', 'callbacks' and 'after' hooks will be dispatched
          automatically when the event is processed by the `simpy` loop.

          .. seealso:: `Event.__call__`

        `Event` is initialized with optional `metadata` attributes,
        provided as keyword args, which will be kept alltogather in
        `Event.metadata` attribute.

        **handlers**:

        Handlers are attached to an `Event` using the `Event.topics`
        list, which is expected to contain a sequence of mappings, each
        mapping holding itself a sequence of callable handlers for a
        given `hook`, for ex ::

            evt = Event()

            topic1 = {
                'before': [h1, h2, h3],
                'after': [h4, h5],
            }

            evt.topics.append(topic1)

        .. note:: a topic is not expected to contain all the possible
            hook keys, it will be ignored if the hook is not found.

        **events dispatching**:

        `Event.dispatcher` holds a dispatcher object (such as
        `EventDispatcher`) that is called by the `Event` when
        dispatching a hook.

        Note setting `Event.dispatcher` to `None` will prevent anything
        from being dispatched for the `Event` instance.

        .. seealso:: `Event.dispatch`

        `Event.enabled` offers a switch to enable / disable dispatching.
        It also allows to notify handlers when the `Event` is enabled or
        disabled, for instance when adding / removing an `Event` in the
        simulation.
    """
    def __init__(self, **metadata):
        """ Initialized a new `Event` object with optional `metadata`

            `metadata` keyword args are kept in `Event.metadata`.
        """
        self.metadata = metadata
        self.topics = []
        self.dispatcher = None
        self._enabled = False

    @property
    def enabled(self):
        """ enable / disable dispatching for the `Event`.

            when the value of `Event.enabled` is changed the following
            hooks are dispatched:

            + **enable** is dispatched just after the value is changed

            + **disable** is dispatched just before the value is changed

            .. seealso:: `Event.dispatch`
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if value != self._enabled:
            if value:
                self._enabled = value
                self.dispatch('enable')
            else:
                self.dispatch('disable')
                self._enabled = value

    def __call__(self, event):
        """ Automatically trigger the `Event` when `event` is processed.

            The `Event` will be attached to the provided
            `simpy.events.Event` object via its callbacks, and the
            following hooks will be dispatched when `event` is processed
            by `simpy` (i.e when its callbacks are called) :

            + **before**: just before `event` is processed
            + **callbacks**: when `event` is processed
            + **after**: just after `event` is processed

            Replaces the `simpy.events.Event` callbacks attribute by a
            `Callbacks` instance so the hooks subscribed to this `Event`
            will be called when the `simpy.events.Event` is processed
            by `simpy`.

            When the `simpy.events.Event` is processed, then calls
            `Event.dispatch` respectively for 'before', 'callbacks' and
            'after' hooks.

            return the `simpy.events.Event` object.

            example usage in a typical `simpy` process ::

                something_happens = Event(name='important', context='test')

                def my_process(env):
                    [...]
                    yield something_happens(env.timeout(1))
        """
        # the partial function is intended to be called by simpy when
        # the event is processed (i.e "f(event)") see class Callbacks
        # for more details.
        _dispatch = self.dispatch
        hooks = []
        for hook in ('before', 'callbacks', 'after'):

            def dispatch(event, hook=hook):
                _dispatch(hook, event)

            hooks.append(dispatch)
        event.callbacks = Callbacks(event, *hooks)
        return event

    def dispatch(self, hook, data=None):
        """ immediately dispatch `hook` for this `Event`.

            + `hook` is the name of the hook to dispatch, for instance
              'before', 'after'...etc.

            + `data` is an optional object to forward to the handlers.
              It will be `None` by default.

            Does nothing if `Event.enabled` is `False` or
            `Event.dispatcher` is `None`.

            calls the `dispatcher.dispatch` method with the following
            arguments:

            + `event`: the `Event` instance
            + `hook`
            + `data`
        """
        if self._enabled:
            dispatcher = self.dispatcher
            if dispatcher is not None:
                dispatcher.dispatch(event=self, hook=hook, data=data)
