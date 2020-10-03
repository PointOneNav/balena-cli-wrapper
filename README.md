# Balena CLI Wrapper

This utility provides support for performing [Balena CLI](https://github.com/balena-io/balena-cli) commands targeting
individual devices by name, rather than UUID.

Device names are generally more human-friendly and easier to remember than UUIDs. Executing device commands by name
makes it easier to be sure that you're performing the command on the intended device. The Balena CLI does not natively
support using device names for device-targeting commands (e.g., `balena ssh`), so this tool wraps calls to the CLI,
using the [Balena Python SDK](https://github.com/balena-io/balena-sdk-python) to query the UUID for a named device.

## Installation

1. Install the Python requirements:
   ```
   pip install -r requirements.txt
   ```
2. Add the `bin/` directory to your `PATH` _before_ the Balena CLI itself (e.g., by editing your `~/.bashrc` file):
   ```
   export PATH="/path/to/balena-cli-wrapper/bin:$PATH"
   ```

## Usage

To use, simply execute Balena CLI commands normally. If you specify a device name for any device-targeting command, it
will be automatically converted to a UUID:

```
> balena ssh my-device
or
> balena ssh f9e118bc8f98e761fcec0ad10f8647b0
```
