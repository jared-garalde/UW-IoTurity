import datetime
import json
from types import SimpleNamespace

class smart_door(object):

    def __init__(self, home_name, code, open_hours):
        self.topic_subs = [(home_name + "/front-door"),
                           (home_name + "/emergency"), (home_name + "/time")]
        self.lock_status = 'locked'
        self.last_status_change = datetime.datetime.now()
        self.current_time = datetime.datetime.now()
        self.date_format = "%d/%m/%Y %H:%M:%S"
        self.open_hours = open_hours
        self.pin_code = code
        self.home = home_name

    def init(self):
        pass

    def set_current_time(self, time_payload):
        try:
            self.current_time = datetime.datetime.strptime(self.current_time.strftime('%d/%m/%Y') + ' ' + time_payload.current_time, "%d/%m/%Y %H:%M:%S")
        except Exception as e:
            print('Unable to set time to the Time provided')
            print(e)

    def check_pin_code(self, payload):
        if hasattr(payload, 'pin_code'):
            pin_matches = payload.pin_code == self.pin_code
            if pin_matches:
                print('Pin Authorized')
                return True
            else:
                print('Incorrect pin code provided')
                return False
        else:
            print('No Pin Code provided')
            return False

    def unlock(self):
        self.lock_status = 'unlocked'
        self.last_status_change = datetime.datetime.now()

    def lock(self):
        self.lock_status = 'locked'
        self.last_status_change = datetime.datetime.now()

    def emergency_response(self, payload):
        # National Emergency Response Codes
        # Todo: These codes need to be validated and operations will need to make sure that they stay up to date
        if payload.emergency_code == 'silver' or payload.emergency_code == 'white' or payload.emergency_code == 'pink':
            self.lock()
        if payload.emergency_code == 'purple' or payload.emergency_code == 'orange' or payload.emergency_code == 'red':
            self.unlock()

    def report_status_json(self):
        return {"status": self.lock_status, "last_changed": self.last_status_change.strftime(self.date_format)}

    def print_door_status(self):
        print(self.home + " front door is " + self.lock_status + ". Current Time: " + self.current_time.strftime(
            self.date_format))

    def is_during_open_hours(self):
        # If check time is not given, default to current UTC time
        check_time = self.current_time
        current_date = self.current_time.strftime('%b %d %Y')
        begin_time = datetime.datetime.strptime(current_date + ' ' + self.open_hours['opening_time'], '%b %d %Y %I:%M%p')
        end_time = datetime.datetime.strptime(current_date + ' ' + self.open_hours['closing_time'], '%b %d %Y %I:%M%p')
        if begin_time < end_time:
            return check_time >= begin_time and check_time <= end_time
        else:  # crosses midnight
            return check_time >= begin_time or check_time <= end_time

    def process_published_message(self, message):
        try:
            payload_string = str(message.payload.decode("utf-8"))
            payload_json_obj = {}
            try:
                payload_json_obj = json.loads(payload_string, object_hook=lambda d: SimpleNamespace(**d))
            except ValueError as json_parse_error:
                print("Unable to Parse JSON. Error Message: " + json_parse_error)
            print("Front Door processing Topic = ", message.topic)
            print("Front Door processing message =", payload_string)
            if message.topic.endswith('emergency'):
                self.emergency_response(payload_json_obj)
            if message.topic.endswith('time'):
                self.set_current_time(payload_json_obj)
            if message.topic.endswith('front-door'):
                during_open_hours = self.is_during_open_hours()
                if not during_open_hours:
                    print('After hours status change request')
                else:
                    if self.check_pin_code(payload_json_obj):
                        if payload_json_obj.state_change_request == 'unlock':
                            self.unlock()
                        if payload_json_obj.state_change_request == 'lock':
                            self.lock()
            self.print_door_status()
        except Exception as e:
            print("Uncaught Error Occurred.  Error:" + e)
