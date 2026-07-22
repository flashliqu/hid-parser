# Windows application

The Windows application is a WPF/WebView2 shell around the repository's
`hid_ui.html`. It uses the same parser, sample descriptor, layout, theme,
highlighting, and automatic parsing behavior as the browser version. The build
embeds `hid_ui.html` directly in the executable, so future UI changes are picked
up without maintaining a second parser implementation.

## Requirements

- A Windows 10 or Windows 11 build computer
- The .NET 8 SDK (the SDK, not only the Desktop Runtime)
- Internet access during the first build so NuGet can restore WebView2
- Microsoft Edge WebView2 Evergreen Runtime on computers running the app

Check that the SDK is available from PowerShell:

```powershell
dotnet --version
```

The command should report version `8.x` or newer.

## Build a self-contained x64 executable

Open PowerShell, change to the repository root, and run:

```powershell
cd C:\path\to\hid-parser
.\windows\build.ps1
```

The script restores dependencies and creates:

```text
artifacts\win-x64\HidDescriptorDecoder.exe
```

This is the normal release build. The .NET runtime, Windows desktop components,
WebView2 loader, and `hid_ui.html` are bundled into one executable. The target
computer still needs the Microsoft Edge WebView2 Evergreen Runtime.

If local PowerShell policy blocks the script, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\build.ps1
```

## Package the executable for distribution

Create a ZIP containing only the finished executable:

```powershell
Compress-Archive `
  -Path .\artifacts\win-x64\HidDescriptorDecoder.exe `
  -DestinationPath .\HID-Descriptor-Decoder-Windows-x64.zip `
  -Force
```

Generated `artifacts` directories, intermediate `bin`/`obj` directories, and
distribution ZIPs are ignored by Git.

## Other build targets

Build for Windows on ARM64:

```powershell
.\windows\build.ps1 -Runtime win-arm64
```

Create a smaller framework-dependent build:

```powershell
.\windows\build.ps1 -FrameworkDependent
```

The framework-dependent version requires the .NET 8 Desktop Runtime on the
target computer. The default self-contained build is recommended for sharing.

## Automated GitHub build

The `Build Windows app` GitHub Actions workflow publishes the x64 executable
when Windows application files or `hid_ui.html` change on `main`. It can also be
started manually with **Actions > Build Windows app > Run workflow**. Download
the result from the workflow run's **Artifacts** section.

## Troubleshooting

- If the app reports that WebView2 is missing, install the Microsoft Edge
  WebView2 Evergreen Runtime and launch it again.
- An unsigned local build may display a Windows SmartScreen warning. Review the
  file, then use **More info > Run anyway** if you trust the build.
- Startup failures are recorded in
  `%LOCALAPPDATA%\HID Descriptor Decoder\startup-error.log`.
- If dependency restore fails, confirm that `https://api.nuget.org` is reachable
  and rerun the build command.
