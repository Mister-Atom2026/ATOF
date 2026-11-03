"""Optional, independently skippable startup videos."""

from pathlib import Path

import pygame


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
VIDEO_DIRECTORY = Path(__file__).resolve().parent / "videos"


def _play_video(screen, path: Path) -> bool:
    try:
        import cv2
    except ImportError:
        return True

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return True
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    clock = pygame.time.Clock()
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return True

            success, frame = capture.read()
            if not success:
                return True
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, screen.get_size())
            surface = pygame.image.frombuffer(frame.tobytes(), screen.get_size(), "RGB")
            screen.blit(surface, (0, 0))
            pygame.display.flip()
            clock.tick(max(1, round(fps)))
    finally:
        capture.release()


def play_intro_videos(screen, directory: Path = VIDEO_DIRECTORY) -> bool:
    """Play bundled videos in filename order; Esc skips only the current video."""
    if not directory.is_dir():
        return True
    videos = sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    return all(_play_video(screen, path) for path in videos)
