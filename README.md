# Signal Gateway

Signal Gateway is a custom Home Assistant integration that provides an alternative for integrating Signal with Home Assistant.

## Features

✨ **Notification Service** - Send Signal messages from Home Assistant (asynchronous REST API)
📱 **Message Reception** - WebSocket listener to capture incoming messages
🔄 **Home Assistant Events** - Automatic relay to `signal_received` events
⚡ **Asynchronous** - Uses `aiohttp` and `websockets` for optimal performance
🚀 **No External Dependencies** - No external dependencies required (excepts for `websockets`)

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

1. Go to **Settings > Devices and Services > Create an Automation**
2. Search for "Signal Gateway"
3. Configure:
   - **Signal CLI API URL**: `http://localhost:8080` (or your server)
   - **Signal Number**: Your Signal number (e.g., `+33612345678`)
   - **Enable WebSocket**: Check to receive messages

## Usage

### Send a Message (Notification Service)

```yaml
service: notify.signal_gateway
data:
  message: "Hello from Home Assistant!"
  data:
    target: "+33612345678"
```

### Event - Messages Received

```yaml
automation:
  - trigger:
      platform: event
      event_type: signal_received
    action:
      - service: logger.log
        data:
          message: "Message received: {{ trigger.event.data }}"
```

## Links / Documentation

- signal-cli-rest-api API Documentation https://bbernhard.github.io/signal-cli-rest-api/#/
- Websockets library used to receive messages from signal-cli-rest-api https://websockets.readthedocs.io/en/stable/

## Requirements

- Home Assistant 2024.1.0 or higher
- [signal-cli-rest-api](https://github.com/spartan737/signal-cli-rest-api) running

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, visit the [Issues](https://github.com/username/signal-gateway/issues) page.

## Contributions

Contributions are welcome! Feel free to submit pull requests.
