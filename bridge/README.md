# Bridge

This folder contains the communication layer between Python tracking and the frontend.

Current contents
- `schema/`: tracker message structure
- `adapters/`: tracker snapshot to outbound message conversion
- `transport/`: websocket server and client broadcast handling

Naming rules
- `*_schema.py`: message contract builders
- `*_adapter.py`: conversion between tracker output and bridge messages
- `*_transport.py`: network transport implementation

Runtime model
- `python_tracker/` produces tracker observations
- `bridge/` shapes and transports them
- `react_frontend/` consumes them
- `runner/` assembles the live application

Canonical runtime entrypoint
- `runner/run_live_tracker.py` is the only supported live entrypoint
