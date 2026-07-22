using System.IO;
using System.Windows;
using System.Windows.Threading;

namespace HidDescriptorDecoder;

public partial class App : Application
{
    static App()
    {
        // This UI does not consume WPF pen or touch events; input belongs to
        // WebView2. Avoid initializing WPF's legacy PenIMC stack, which can be
        // unavailable on some Windows installations and is unnecessary here.
        AppContext.SetSwitch(
            "Switch.System.Windows.Input.Stylus.DisableStylusAndTouchSupport",
            true);
    }

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        DispatcherUnhandledException += OnDispatcherUnhandledException;

        try
        {
            var window = new MainWindow();
            MainWindow = window;
            window.Show();
        }
        catch (Exception ex)
        {
            ReportFatalStartupError(ex);
            Shutdown(-1);
        }
    }

    private static void OnUnhandledException(object sender, UnhandledExceptionEventArgs e)
    {
        var exception = e.ExceptionObject as Exception
            ?? new Exception(e.ExceptionObject?.ToString() ?? "Unknown application error.");
        WriteCrashLog(exception);
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        ReportFatalStartupError(e.Exception);
        e.Handled = true;
        Shutdown(-1);
    }

    private static void ReportFatalStartupError(Exception exception)
    {
        var logPath = WriteCrashLog(exception);
        MessageBox.Show(
            $"The application could not start.\n\n{exception.Message}\n\nDiagnostic details were written to:\n{logPath}",
            "HID Report Descriptor Decoder",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }

    private static string WriteCrashLog(Exception exception)
    {
        var localData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var logDirectory = Path.Combine(localData, "HID Descriptor Decoder");
        var logPath = Path.Combine(logDirectory, "startup-error.log");

        try
        {
            Directory.CreateDirectory(logDirectory);
            File.WriteAllText(
                logPath,
                $"HID Report Descriptor Decoder startup failure\n" +
                $"UTC: {DateTime.UtcNow:O}\n" +
                $"OS: {Environment.OSVersion}\n" +
                $"64-bit OS: {Environment.Is64BitOperatingSystem}\n" +
                $"64-bit process: {Environment.Is64BitProcess}\n\n" +
                exception);
        }
        catch
        {
            // Preserve the original startup error even if diagnostics cannot be saved.
        }

        return logPath;
    }
}
