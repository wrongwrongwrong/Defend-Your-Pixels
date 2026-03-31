# Bridge

This folder contains the communication layer between Python tracking and the frontend.

Current contents
- `websocket_server.py`: captures camera frames, detects ArUco markers, maps board coordinates, and broadcasts tracker state over WebSocket.

Planned additions
- shared state schema
- transport adapters
- contract examples for frontend consumers
