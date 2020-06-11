from datetime import datetime
from time import sleep
import filecmp

from quokka.controller.device_info import get_device_info
from quokka.models.Compliance import Compliance
from quokka.models.apis import get_all_devices
from quokka.models.apis import set_device


def check_os_compliance(device):

    standard = Compliance.query.filter_by(**{"vendor": device["vendor"], "os": device["os"]}).one_or_none()
    if standard is None:
        print(f"!!! Error retrieving compliance record for this device {device['name']}")
        return False

    try:
        result, facts = get_device_info(device["name"], "facts", get_live_info=True)
    except BaseException as e:
        print(f"!!! Exception getting device info in compliance monitoring for {device['name']}")

    if result == "success":
        if standard.standard_version == facts["facts"]["os_version"]:
            return True
        else:
            return False  # Just a normal incorrect version
    else:
        print(f"!!! Error retrieving version info for this device {device['name']}")
        return False


def check_config_compliance(device):

    standard = Compliance.query.filter_by(**{"vendor": device["vendor"], "os": device["os"]}).one_or_none()
    if standard is None:
        print(f"!!! Error retrieving compliance record for this device {device['name']}")
        return False

    standard_filename = "quokka/data/" + standard.standard_config_file

    result, config = get_device_info(device["name"], "config")
    if result != "success" or "config" not in config or "running" not in config["config"]:
        print(f"!!! Error retrieving running config for this device {device['name']}")
        return False

    config_running = config["config"]["running"]

    try:
        # standard_filename = "quokka/data/" + device["vendor"] + "." + device["os"] + "." + "standard.config"
        with open(standard_filename, "r") as config_out:
            config_standard = config_out.read()
    except (FileExistsError, FileNotFoundError) as e:
        print(f"!!! Error retrieving compliance standard file {standard_filename} for device {device['name']}")
        return False

    if config_running != config_standard:
        with open(standard_filename.replace("standard", "running" + "." + device["name"]), "w") as config_out:
            config_out.write(config_running)
        return False

    return True


class ComplianceMonitorTask:

    def __init__(self):
        self.terminate = False

    def set_terminate(self):
        self.terminate = True
        print(self.__class__.__name__, "monitor:compliance Terminate pending")

    def monitor(self, interval):

        while True and not self.terminate:

            devices = get_all_devices()
            print(f"Monitor: Beginning monitoring for {len(devices)} devices")
            for device in devices:

                if self.terminate:
                    break

                print(f"--- monitor:compliance get environment {device['name']}")
                try:
                    result, env = get_device_info(device["name"], "environment")
                except BaseException as e:
                    print(f"!!! Exception in monitoring compliance: {repr(e)}")
                    continue

                if result != "success":
                    device["availability"] = False

                else:
                    device["os_compliance"] = check_os_compliance(device)
                    device["config_compliance"] = check_config_compliance(device)
                    device["last_compliance_check"] = str(datetime.now())[:-3]

                set_device(device)

            for _ in range(0, int(interval / 10)):
                sleep(10)
                if self.terminate:
                    break

        print("...gracefully exiting monitor:compliance")