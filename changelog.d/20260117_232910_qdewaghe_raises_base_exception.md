### Fixed

- `raises` catches BaseException instead of Exception. This ensures that SystemExit and KeyboardInterrupt are also caught.
