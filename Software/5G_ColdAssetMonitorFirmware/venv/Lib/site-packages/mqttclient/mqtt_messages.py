import re

from onoff import OnOffMixin

class MqttMessages(OnOffMixin):
    """
       Mixins for listening and subscribing to mqtt messages,
       with helpers to automate common app framework uri structures like:
       state, put, notify, status, trigger, and signal.
       
       These mixins only automate the naming conventions
       and the expected retain behaviour.
    """
    
    def add_subscription(self, channel, method):

        def m(payload, args):
            if 'route_name' in args:
                del args['route_name']
            vals = args.values()
            return method(*vals, payload)

        self.router.add_route(channel, m)
        subscription = re.sub(r"\{(.+?)\}", "+", channel)

        if not self.connected:
            print(f'{this.name} :: Can not add subscription, disconnected')
            return subscription

        if subscription in self.subscriptions:
            return subscription

        self.subscriptions.append(subscription)
        self.client.subscribe(subscription)

        return subscription

    def add_binding(self, channel, event, retain=False, qos=0, dup=False):
        return self.on(event, lambda d: self.send_message(channel,
                                                         d, retain, qos, dup))

    def on_state_msg(self, sender, val, method):
        return self.add_subscription(f'{self.base}/{sender}/state/{val}', method)

    def bind_state_msg(self, val, event, persist=True):
        return self.add_binding(f'{self.base}/{self.name}/state/{val}', event, persist)

    def on_put_msg(self, val, method):
        return self.add_subscription(f'{self.base}/put/{self.name}/{val}', method)

    def bind_put_msg(self, receiver, val, event):
        return self.add_binding(f'{self.base}/put/{receiver}/{val}', event)

    def on_notify_msg(self, sender, topic, method):
        return self.add_subscription(f'{self.base}/{sender}/notify/{self.name}/{topic}', method)

    def bind_notify_msg(self, receiver, topic, event):
        return self.add_binding(f'{self.base}/{name}/notify/{receiver}/{topic}', event)

    def on_status_msg(self, sender, method):
        return self.add_subscription(f'{self.base}/status/{sender}', method)

    def bind_status_msg(self, event):
        return self.add_binding(f'{self.base}/status/{self.name}', event)

    def on_trigger_msg(self, action, method):
        return self.add_subscription(f'{self.base}/trigger/{self.name}/action', method)

    def bind_trigger_msg(self, receiver, action, event):
        return self.add_binding(f'{self.base}/trigger/{receiver}/{action}', event)

    def on_signal_msg(self, sender, topic, method):
        return self.add_subscription(f'{self.base}/{sender}/signal/{topic}', method)

    def bind_signal_msg(self, topic, event):
        return self.add_binding(f'{self.base}/{self.name}/signal/{topic}', event)
