# Bridge

This folder contains the communication layer between Python tracking and the frontend.

Current contents
- `schema/`: tracker message structure
- `adapters/`: tracker snapshot to outbound message conversion
- `transport/`: websocket server and client broadcast handling
- `run_live_bridge.py`: bridge-level entrypoint that forwards to the live runner
- `websocket_server.py`: legacy compatibility wrapper kept for old command paths

Naming rules
- `*_schema.py`: message contract builders
- `*_adapter.py`: conversion between tracker output and bridge messages
- `*_transport.py`: network transport implementation

Runtime model
- `python_tracker/` produces tracker observations
- `bridge/` shapes and transports them
- `react_frontend/` consumes them
- `runner/` assembles the live application
