import cv2
import numpy as np

def get_board_corners(corners, ids):
    """
    Find the four corners of the board from detected markers
    ID 0 = top-left, ID 1 = top-right, ID 2 = bottom-left, ID 3 = bottom-right
    """
    board_corners = {}
    if ids is None:
        return board_corners
    
    for i, marker_id in enumerate(ids.flatten()):
        if marker_id in [0, 1, 2, 3]:
            # Get the center point of the marker
            center = corners[i][0].mean(axis=0)
            board_corners[marker_id] = center
    
    return board_corners

def pixel_to_grid(px, py, board_corners, grid_cols=12, grid_rows=12):
    """
    Convert pixel coordinates to grid coordinates
    Returns (grid_x, grid_y, lane)
    lane = 'A', 'B', 'C' or None
    """
    # Check if all four corners are found
    if not all(k in board_corners for k in [0, 1, 2, 3]):
        return None, None, None
    
    # Get board boundaries
    top_left = board_corners[0]
    top_right = board_corners[1]
    bottom_left = board_corners[2]
    
    board_width = top_right[0] - top_left[0]
    board_height = bottom_left[1] - top_left[1]
    
    # Convert to grid coordinates
    grid_x = int(((px - top_left[0]) / board_width) * grid_cols)
    grid_y = int(((py - top_left[1]) / board_height) * grid_rows)
    
    # Clamp values within valid range
    grid_x = max(0, min(grid_cols - 1, grid_x))
    grid_y = max(0, min(grid_rows - 1, grid_y))
    
    # Determine lane based on horizontal position
    if grid_x < grid_cols // 3:
        lane = 'A'
    elif grid_x < (grid_cols // 3) * 2:
        lane = 'B'
    else:
        lane = 'C'
    
    return grid_x, grid_y, lane

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)

    print("Press 'esc' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        corners, ids, _ = detector.detectMarkers(frame)

        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            
            # Find board corners
            board_corners = get_board_corners(corners, ids)
            
            # Convert each token position to grid coordinates
            for i, marker_id in enumerate(ids.flatten()):
                # Only process tokens (ID 10-13)
                if marker_id in [10, 11, 12, 13]:
                    center = corners[i][0].mean(axis=0)
                    px, py = int(center[0]), int(center[1])
                    
                    grid_x, grid_y, lane = pixel_to_grid(px, py, board_corners)
                    
                    if lane:
                        token_type = "ATK" if marker_id in [10, 11] else "DEF"
                        print(f"{token_type} (ID {marker_id}) → Lane {lane}, Grid ({grid_x}, {grid_y})")
                        
                        # Display result on screen
                        cv2.putText(frame, f"{token_type} Lane {lane}",
                            (px, py - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Pixel Defense Tracker", frame)

        if cv2.waitKey(1) & 0xFF == ord('27'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()