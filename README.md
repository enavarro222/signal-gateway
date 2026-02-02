# Signal Gateway

[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/enavarro222/signal-gateway/ci.yml?branch=main&style=flat-square&label=tests)](https://github.com/enavarro222/signal-gateway/actions)
[![codecov](https://img.shields.io/codecov/c/github/enavarro222/signal-gateway?style=flat-square)](https://codecov.io/gh/enavarro222/signal-gateway)
[![License](https://img.shields.io/github/license/enavarro222/signal-gateway?style=flat-square)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12+-41BDF5.svg?style=flat-square)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)

Signal Gateway is a custom integration that provides an alternative for integrating Signal with Home Assistant.
The main difference with the official [Signal Messenger](https://www.home-assistant.io/integrations/signal_messenger/) integration
is the ability to receive messages from Signal Messenger REST API in real time using WebSockets.

## Features

- ✨ **Notification Service** - Send Signal messages from Home Assistant (asynchronous REST API)
- 📱 **Message Reception** - WebSocket listener to capture incoming messages
- 🔄 **Home Assistant Events** - Automatic relay to `signal_received` events
- ⚡ **Asynchronous** - Uses `aiohttp` for optimal performance
- 🚀 **No External Dependencies** - No additional Python packages required

## Installation

### Via HACS

1. Add this repository to HACS as a custom repository
2. Search for "Signal Gateway" in HACS
3. Install the integration
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/signal_gateway` directory into your Home Assistant `custom_components` folder
2. Restart Home Assistant

## Quick Setup

1. Go to **Settings > Devices and Services > Add Integration**
2. Search for "Signal Gateway"
3. Configure:
   - **Name**: The name of your Signal Gateway integration (default: "Signal")
   - **Signal CLI API URL**: URL of your signal-cli-rest-api server (e.g., `http://localhost:8080`)
   - **Phone Number**: Your Signal sender number in international format with country code (e.g., `+33612345678`)
   - **Default Recipients** (optional): Phone numbers to send to by default (one per line, e.g., `+33687654321`)
   - **Enable WebSocket listener**: Enable to receive incoming messages in real-time

### Migrating from Official Signal Messenger Integration

If you're replacing the official [Signal Messenger](https://www.home-assistant.io/integrations/signal_messenger/) integration:

1. **Remove the official integration** from your `configuration.yaml`:
   ```yaml
   # Remove or comment out these lines in notify section:
   notify:
   # - name: signal
   #    platform: signal_messenger
   #    url: "http://127.0.0.1:8080"
   #    number: "+33612345678"
   #    recipients:
   #      - "+33687654321"
   ```

2. **Restart Home Assistant** to unload the official integration

3. **Install Signal Gateway** following the Quick Setup above

4. **Name your service "Signal"** during configuration - this ensures the notification service is named `notify.signal`, maintaining compatibility with existing automations

5. **Your existing automations will work without changes** - all calls to `notify.signal` will automatically use Signal Gateway instead of the official integration

**Note:** Signal Gateway uses the same signal-cli-rest-api backend, so no changes to your Signal server setup are needed.

## Usage

### Send a Message (Notification Service)

The integration creates a notification service named based on your configured integration name (e.g., `notify.signal` for default name).

**Basic message:**
```yaml
service: notify.signal
data:
  message: "Hello from Home Assistant!"
  target: "+33612345678"
```

**With title:**
```yaml
service: notify.signal
data:
  title: "Alert"
  message: "Temperature is above threshold!"
  target: "+33612345678"
```

**Multiple recipients:**
```yaml
service: notify.signal
data:
  message: "Notification for multiple people"
  target:
    - "+33612345678"
    - "+33687654321"
```

**Send to a group:**
```yaml
service: notify.signal
data:
  message: "Hello everyone in the group!"
  target: "group.Unp6dnAxbGZCWDNiVmpLdWFyYXlJQUFGRDladlFJbS81WVhwdEdDZHR5RT0="
```

> **Note:** To get your group ID, call the signal-cli-rest-api endpoint:
> `GET http://your-api:8080/v1/groups/+yourphonenumber`
> Use the `id` field (starts with `group.`), not the `internal_id`.

**With local file attachments:**
```yaml
service: notify.signal
data:
  message: "Check this camera snapshot"
  target: "+33612345678"
  data:
    attachments:
      - "/config/www/camera_snapshot.jpg"
      - "/config/www/photo.png"
```

**With URL attachments:**
```yaml
service: notify.signal
data:
  message: "Weather map"
  target: "+33612345678"
  data:
    urls:
      - "https://example.com/weather_map.png"
    verify_ssl: true  # Optional, default is true
```

**Combining local files and URLs:**
```yaml
service: notify.signal
data:
  message: "Multiple attachments"
  target: "+33612345678"
  data:
    attachments:
      - "/config/www/local_file.jpg"
    urls:
      - "https://example.com/remote_image.png"
```

**Using default recipients** (if configured):
```yaml
service: notify.signal
data:
  message: "This goes to default recipients"
```

### Text Formatting

Signal Gateway supports **styled text formatting** (similar to Markdown) when explicitly enabled:

**Formatting syntax** (requires `text_mode: "styled"`):
- `*text*` → *italic text*
- `**text**` → **bold text**
- `~text~` → ~~strikethrough text~~
- `` `text` `` → `monospace text`
- `||text||` → spoiler text (hidden until clicked)

**Example with formatted text:**
```yaml
service: notify.signal
data:
  message: |
    **Alert!** Temperature is *above* threshold.
    Current value: `25.5°C`
    ~Old value: 20°C~
  target: "+33612345678"
  data:
    text_mode: "styled"  # Enable formatting
```

**Default behavior** (plain text mode):
```yaml
service: notify.signal
data:
  message: "**This will be sent as-is, not bold**"
  target: "+33612345678"
  # text_mode defaults to "normal" for compatibility with official integration
```

> **Note:** The default `text_mode` is `"normal"` (plain text) for compatibility with the official Signal Messenger integration. Set `text_mode: "styled"` to enable markdown-like formatting.

### Receive Messages (Event Automation)

When WebSocket listener is enabled, incoming messages trigger `signal_received` events:

```yaml
automation:
  - alias: "Log received Signal messages"
    trigger:
      platform: event
      event_type: signal_received
    action:
      - service: logger.log
        data:
          message: "Message received: {{ trigger.event.data }}"
```

**Example - Respond to specific message:**
```yaml
automation:
  - alias: "Respond to home command"
    trigger:
      platform: event
      event_type: signal_received
    condition:
      - condition: template
        value_template: "{{ 'home' in trigger.event.data.message | lower }}"
    action:
      - service: notify.signal
        data:
          message: "Welcome home!"
          target: "{{ trigger.event.data.sender }}"
```

## Configuration

### Attachment Support

The integration supports two types of attachments:

**Local Files:**
- Provide absolute file paths accessible from Home Assistant
- Files are automatically validated (existence, readability)
- Automatically encoded to base64 before sending
- Supports `file://` URL scheme (automatically stripped)

**Remote URLs:**
- Download files from HTTP/HTTPS URLs
- Maximum download size: 50 MB per file
- SSL certificate verification (can be disabled with `verify_ssl: false`)
- Files are downloaded and encoded to base64 automatically

**Important Notes:**
- Both attachment types can be combined in a single message
- All files (local and remote) are base64-encoded automatically


### Multiple Instances

You can configure multiple Signal Gateway instances with different names to use different Signal accounts:

1. Add another integration instance with a unique name (e.g., "Signal Work")
2. This creates a separate service: `notify.signal_work`

### Updating Configuration

To modify your configuration:
1. Go to **Settings > Devices and Services**
2. Find your Signal Gateway integration
3. Click **Configure** to update settings
4. The integration will automatically reload with new settings

## Requirements

- Home Assistant 2024.1.0 or higher
- [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) server running and accessible
  - You can use the [Home Assistant Add-on](https://github.com/haberda/hassio_addons) to easily run signal-cli-rest-api
  - **Important:** You must first register/configure a phone number in signal-cli-rest-api before using this integration. See the [setup guide](https://github.com/bbernhard/signal-cli-rest-api/blob/master/doc/HOMEASSISTANT.md#set-up-a-phone-number) for instructions.

## Links / Documentation

- [signal-cli-rest-api API Documentation](https://bbernhard.github.io/signal-cli-rest-api/#/)
- [signal-cli-rest-api Home Assistant Add-on](https://github.com/haberda/hassio_addons)
- [Phone Number Registration Guide](https://github.com/bbernhard/signal-cli-rest-api/blob/master/doc/HOMEASSISTANT.md#set-up-a-phone-number)
- [aiohttp WebSocket Client Documentation](https://docs.aiohttp.org/en/stable/client_quickstart.html#websockets)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, visit the [Issues](https://github.com/enavarro222/signal-gateway/issues) page.

## Contributions

Contributions are welcome! Feel free to submit pull requests.

### Development Setup

To set up the development environment:

1. Clone the repository
2. Install dependencies: `pip install -r requirements-dev.txt`
3. Install git hooks: `make install-hooks`
4. Run tests: `make tests`

The git hooks will automatically run code formatting (black), linting (pylint), and type checking (mypy) before each commit.
**Available Make targets:**
- `make check` - Run all code quality checks (format + lint)
- `make format` - Check code formatting with black
- `make lint` - Run pylint and mypy
- `make tests` - Run test suite with coverage
- `make install-hooks` - Install git pre-commit hooks
- `make run` - Start Home Assistant for development
