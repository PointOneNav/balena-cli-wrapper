from argparse import ArgumentParser
import logging
import os
import re
import sys

from balena.base_request import BaseRequest
from balena.exceptions import DeviceNotFound

# Relative imports don't usually work when running a Python file as a script since the file is not considered to be part
# of a package. To get around this, we add the repo root directory to the import search path and set __package__ so the
# interpreter tries the relative imports based on `<__package__>.__main__` instead of just `__main__`.
if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    repo_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.append(repo_dir)
    import point_one.balena
    __package__ = "point_one.balena"

from .auth import authenticate

__logger = logging.getLogger("point_one.balena.device")


def get_device_uuid(name_or_uuid, is_name=None, return_name=False, balena=None, auth_token=None,
                    check_exact_match=False):
    if balena is None:
        balena = authenticate(auth_token)

    #If this might be a 128 - bit UUID, first see if we can find a device with it.
    name = None
    uuid = None
    uuid_like = re.match(r"^[a-fA-F0-9]+$", name_or_uuid)
    full_uuid_length = len(name_or_uuid) == 32
    if uuid_like and not is_name and full_uuid_length:
        __logger.debug("Trying absolute UUID query for '%s'." % name_or_uuid)

        try:
            name = balena.models.device.get_name(name_or_uuid)
            uuid = name_or_uuid
            __logger.debug("Found device %s (%s) by absolute UUID." % (name, uuid))
        except DeviceNotFound:
            pass

    # If this might be a device name, look now.
    devices_by_name = []
    if uuid is None and is_name is not False:
        __logger.debug("Trying device name query for '%s'." % name_or_uuid)

        # Unfortunately, Balena's Python SDK does not have an efficient way to do a partial name match, but we can make
        # a custom request manually. See https://forums.balena.io/t/python-sdk-partial-device-uuid-query/190973/33.
        request = BaseRequest()
        devices_by_name = request.request('device', 'GET',
                                          raw_query="$filter=startswith(device_name, '%s')" % name_or_uuid,
                                          endpoint=balena.settings.get('pine_endpoint'))['d']
        for device in devices_by_name:
            device['name'] = device['device_name']

        if len(devices_by_name) == 1:
            device = devices_by_name[0]
            if is_name:
                uuid = device['uuid']
                name = device['name']
                __logger.debug("Found device %s (%s) by name." % (name, uuid))
            else:
                __logger.debug("Found candidate device %(name)s (%(uuid)s) by name." % device)
        elif len(devices_by_name) > 1:
            __logger.warning("Found multiple devices matching partial name string:\n    %s" %
                             "\n    ".join(["%(name)s (%(uuid)s)" % device for device in devices_by_name]))

            # If any of the devices is an exact match to the name, assume that's the correct match.
            if check_exact_match:
                for device in devices_by_name:
                    if device['name'] == name_or_uuid:
                        uuid = device['uuid']
                        name = device['name']
                        __logger.warning("Using exact match: %s (%s)." % (name, uuid))

    # If it's UUID-like and not explicitly a device name, see if it matches any known device.
    devices_by_uuid = []
    if uuid is None and not is_name and uuid_like and not full_uuid_length:
        __logger.debug("Trying partial UUID query for '%s'." % name_or_uuid)

        # Unfortunately, Balena's Python SDK does not have an efficient way to do a partial UUID match, but we can make
        # a custom request manually. See https://forums.balena.io/t/python-sdk-partial-device-uuid-query/190973/33.
        request = BaseRequest()
        devices_by_uuid = request.request('device', 'GET',
                                          raw_query="$filter=startswith(uuid, '%s')" % name_or_uuid,
                                          endpoint=balena.settings.get('pine_endpoint'))['d']
        for device in devices_by_uuid:
            device['name'] = device['device_name']

        if len(devices_by_uuid) == 1:
            device = devices_by_uuid[0]
            if is_name is not None:
                uuid = device['uuid']
                name = device['name']
                __logger.debug("Found device %s (%s) by partial UUID match." % (name, uuid))
            else:
                __logger.debug("Found candidate device %(name)s (%(uuid)s) by partial UUID match." % device)
        elif len(devices_by_uuid) > 1:
            __logger.warning("Found multiple devices matching partial UUID string:\n    %s" %
                             "\n    ".join(["%(name)s (%(uuid)s)" % device for device in devices_by_uuid]))

    if uuid is None:
        num_devices = len(devices_by_name) + len(devices_by_uuid)
        if num_devices > 1:
            raise ValueError("Found multiple devices matching query string.")
        elif len(devices_by_name) == 1:
            uuid = devices_by_name[0]['uuid']
            name = devices_by_name[0]['name']
        elif len(devices_by_uuid) == 1:
            uuid = devices_by_uuid[0]['uuid']
            name = devices_by_uuid[0]['name']
        else:
            raise DeviceNotFound("No device found matching query string.")

    __logger.debug("Returning %s (%s)." % (name, uuid))
    if return_name:
        return uuid, name
    else:
        return uuid


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('name_or_uuid', type=str,
                        help="The (partial or complete) device name or UUID to query.")

    parser.add_argument('--get-name', action='store_true',
                        help="Return the name of the located device instead of its UUID.")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--name', action='store_true',
                       help="If specified, treat the string as a name and do not attempt a UUID lookup.")
    group.add_argument('--uuid', action='store_true',
                       help="If specified, treat the string as a UUID and do not attempt a name lookup.")

    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Print verbose/trace debugging messages.")

    options = parser.parse_args()

    if options.verbose == 1:
        logging.basicConfig()
        __logger.setLevel(logging.DEBUG)
    elif options.verbose > 1:
        # Enable debug messages all libraries including the Balena SDK.
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(message)s')

    if options.name:
        is_name = True
    elif options.uuid:
        is_name = False
    else:
        is_name = None

    try:
        uuid, name = get_device_uuid(options.name_or_uuid, is_name=is_name, return_name=True)
        if options.get_name:
            print(name)
        else:
            print(uuid)
    except Exception as e:
        __logger.error("Error: %s" % str(e))
        sys.exit(1)
