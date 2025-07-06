# GameTrace

GameTrace is a lightweight, user-friendly tool designed for recording gameplay while capturing keyboard and mouse inputs. It's built to deliver a seamless recording experience with minimal resource consumption, supporting multiple platforms.

## Features

- **Cross-Platform Compatibility**  
  Works seamlessly on both Windows and macOS.

- **User-Friendly Interface**  
  - One-click start for instant recording.  
  - Select recording area to focus on specific regions.  
  - Automatically records keyboard and mouse events during gameplay.  
  - One-click upload for sharing or backup.

- **Resource Efficiency**  
  Optimized to minimize memory and CPU usage, ensuring smooth gameplay even while recording.

## Installation

### Install from source code

First, download ffmpeg from `https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-7.0.2-full_build.7z`

Second, unzip the ffmpeg file and then copy `ffmpeg.exe` to the project root dir.

Finally, execute the following command to pack the .exe program. (use `--add-binary "ffmpeg.exe;."` to pack the ffmpeg into the final .exe file)

```bash
pip install pynput numpy psutil
pip install pyinstaller
pyinstaller recorder_app.py --onefile --add-binary "ffmpeg.exe;."
```




<!-- ### Windows

1. Download the latest release from [Releases](https://github.com/yourusername/GameTrace/releases).  
2. Extract the archive and run the installer.  
3. Follow the setup instructions to complete the installation.

### macOS

1. Download the latest release from [Releases](https://github.com/yourusername/GameTrace/releases).  
2. Open the downloaded `.dmg` file and drag the app to your Applications folder.  
3. Launch the app and grant necessary permissions if prompted. -->

## Usage
<!-- 
1. Launch **GameTrace** on your system.  
2. Follow GPT to open **立体声混音**/**Stereo Mix** in your device. If it was open, skip this step.
3. Select your desired recording options:  
   - Full-screen or region-specific recording.  
   - Enable/disable keyboard and mouse input logging.  
4. Click the **Start Recording** button to begin.  
5. Once finished, click **Stop Recording**.  
6. Optionally, upload your recording with the **Upload** button. -->

1. Launch **GameTrace** on your system.  
2. Follow GPT to open **立体声混音**/**Stereo Mix** in your device. If it was open, skip this step.
3. Select your desired recording options:  
   - Full-screen or region-specific recording.  
   - Enable/disable keyboard and mouse input logging.  
4. Click the **Start Recording** button to begin.  
5. Once finished, click **Stop Recording**.  
6. Optionally, upload your recording with the **Upload** button.

## Contributing

We welcome contributions from the community! If you'd like to improve or extend GameTrace, please follow these steps:  
1. Fork the repository.  
2. Create a new branch (`git checkout -b feature-branch`).  
3. Commit your changes (`git commit -am 'Add new feature'`).  
4. Push to the branch (`git push origin feature-branch`).  
5. Open a pull request.

## License

GameTrace is released under the [MIT License](https://github.com/yourusername/GameTrace/blob/main/LICENSE).

---

### Feedback & Support

Feel free to submit issues or feature requests in the [Issues](https://github.com/yourusername/GameTrace/issues) section of the repository. We'd love to hear from you!
