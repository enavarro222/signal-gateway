# Signal Gateway

Signal Gateway is a custom integration that provides an alternative for integrating Signal with Home Assistant.
The main difference with the official [Signal Messenger](https://www.home-assistant.io/integrations/signal_messenger/) integration
is the ability to receive messages from Signal Messenger REST API in real time using WebSockets.

## Features

✨ **Notification Service** - Send Signal messages from Home Assistant (asynchronous REST API)
📱 **Message Reception** - WebSocket listener to capture incoming messages
🔄 **Home Assistant Events** - Automatic relay to `signal_received` events
⚡ **Asynchronous** - Uses `aiohttp` for optimal performance
🚀 **No External Dependencies** - No additional Python packages required

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

**With local file attachments:**
```yaml
service: notify.signal
data:
  message: "Check this camera snapshot"
  target: "+33612345678"
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
