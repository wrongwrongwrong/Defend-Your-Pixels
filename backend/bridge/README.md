# Bridge

This folder contains the communication layer between Python tracking and the frontend.

Current contents
- `transport/`: websocket server and client broadcast handling

Naming rules
- `*_schema.py`: message contract builders
- `*_adapter.py`: conversion between tracker output and bridge messages
- `*_transport.py`: network transport implementation

Note: only `transport/` exists in the current bridge implementation. The naming rules are kept for future additions and for reading older docs.

Runtime model
- `backend/python_tracker/` produces tracker observations
- `backend/bridge/` shapes and transports them
- `frontend/index.html` consumes them through the live runtime HTTP/WS path
- `runner/` assembles the live application

Canonical runtime entrypoint
- `runner/run_live_tracker.py` is the only supported live entrypoint
