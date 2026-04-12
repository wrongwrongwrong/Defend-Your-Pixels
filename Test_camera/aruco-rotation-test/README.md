# ArUco Rotation Test

Detects **DICT_4X4_50** ArUco markers through a phone camera and maps their
rotation angle to a game direction.

| Rotation | Direction    | Colour |
|----------|-------------|--------|
| 0°       | ATTACK HQ   | Green  |
| 90°      | ATTACK RIGHT | Blue  |
| 180°     | DEFEND       | Red   |
| 270°     | ATTACK LEFT  | Yellow |

Marker IDs in use:
- **0–3** — board corner markers
- **10–13** — token markers

---

## 1. Install requirements

```bash
pip install -r requirements.txt
```

> If you already have `opencv-python` installed, uninstall it first:
> `pip uninstall opencv-python` — the two packages conflict.

---

## 2. Set up DroidCam on your phone

1. Install the **DroidCam** app on your Android or iOS device.
2. Open the app — it will display the phone's **IP address** and **port** (default `4747`).
3. Make sure your phone and computer are on the **same Wi-Fi network**.

---

## 3. Change the IP address in the code

Open `main.py` and edit the two lines near the top:

```python
PHONE_IP   = "192.168.1.100"   # <-- replace with the IP shown in DroidCam
PHONE_PORT = 4747              # change only if DroidCam shows a different port
```

### Test with your computer webcam first

If you want to verify the detection logic before connecting a phone, set:

```python
USE_WEBCAM = True
```

---

## 4. Run the project

```bash
python main.py
```

---

## 5. What to expect

- A window titled **"ArUco Rotation Test"** opens showing the live camera feed.
- Each detected marker is outlined in cyan. A yellow dot marks its **top-left corner**
  (the reference corner used to compute orientation).
- Above each marker you will see:
  - The **marker ID**
  - The **rotation angle** in degrees
  - The **direction label** in its assigned colour
- The same information is printed to the terminal whenever the set of visible
  markers changes.
- Press **`q`** to quit.

---

## 6. WebSocket + Phaser.js mode

This mode runs `server.py` instead of `main.py`. It does everything `main.py`
does **plus** broadcasts each detected marker over a WebSocket so a Phaser.js
page can display the result in real time.

### Install the extra dependency

```bash
pip install websockets
# or just re-run:
pip install -r requirements.txt
```

### Run the WebSocket server

```bash
python server.py
```

You will see:
```
=== ArUco WebSocket Server ===
WebSocket : ws://localhost:8765
Camera    : webcam
```

The camera window opens exactly like `main.py`. Detection results are printed
to the terminal **and** broadcast to any connected browser.

### Open the Phaser display

Simply open `index.html` in your browser (double-click the file, or drag it
into Chrome/Firefox). No web server needed — it connects to `localhost:8765`
automatically.

### What to expect

- The page shows a **6 × 6 grid** with a coloured square token in the centre.
- "Waiting for connection..." is shown until `server.py` is running.
- When a marker is detected the token changes colour to match the direction:

| Direction    | Colour |
|-------------|--------|
| ATTACK HQ   | Green  |
| ATTACK RIGHT | Blue  |
| DEFEND       | Red   |
| ATTACK LEFT  | Yellow |

- The direction label appears above the token.
- The marker ID and angle are shown in the top-left corner.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Could not open camera" | Check the IP/port; ensure phone and PC are on the same network |
| Video is choppy | Lower the resolution in the DroidCam app settings |
| No markers detected | Ensure good lighting and hold the marker flat toward the camera |
| Wrong direction shown | Re-orient the marker so its printed "top" faces the target direction |
