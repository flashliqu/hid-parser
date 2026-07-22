using System.IO;
using System.Reflection;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace HidDescriptorDecoder;

public partial class MainWindow : Window
{
    private const string VirtualHostName = "hid-decoder.local";
    private const string UiResourceName = "HidDescriptorDecoder.Web.hid_ui.html";

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        Loaded -= OnLoaded;

        try
        {
            var localData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var appDataFolder = Path.Combine(localData, "HID Descriptor Decoder");
            var webRoot = Path.Combine(appDataFolder, "Web");
            var userDataFolder = Path.Combine(appDataFolder, "WebView2");
            ExtractEmbeddedUi(webRoot);
            Directory.CreateDirectory(userDataFolder);

            var environment = await CoreWebView2Environment.CreateAsync(
                browserExecutableFolder: null,
                userDataFolder: userDataFolder);

            await Browser.EnsureCoreWebView2Async(environment);
            Browser.CoreWebView2.SetVirtualHostNameToFolderMapping(
                VirtualHostName,
                webRoot,
                CoreWebView2HostResourceAccessKind.DenyCors);

            Browser.Source = new Uri($"https://{VirtualHostName}/hid_ui.html");
        }
        catch (WebView2RuntimeNotFoundException)
        {
            ShowFatalError(
                "Microsoft Edge WebView2 Runtime is required.",
                "Install the Evergreen WebView2 Runtime from Microsoft, then start the application again.\n\nhttps://developer.microsoft.com/microsoft-edge/webview2/");
        }
        catch (Exception ex)
        {
            ShowFatalError("The application could not start.", ex.Message);
        }
    }

    private static void ExtractEmbeddedUi(string webRoot)
    {
        Directory.CreateDirectory(webRoot);

        using var source = Assembly.GetExecutingAssembly().GetManifestResourceStream(UiResourceName)
            ?? throw new InvalidOperationException($"Embedded UI resource '{UiResourceName}' was not found.");
        using var destination = new FileStream(
            Path.Combine(webRoot, "hid_ui.html"),
            FileMode.Create,
            FileAccess.Write,
            FileShare.Read);
        source.CopyTo(destination);
    }

    private void ShowFatalError(string title, string message)
    {
        MessageBox.Show(this, message, title, MessageBoxButton.OK, MessageBoxImage.Error);
        Close();
    }

    protected override void OnClosed(EventArgs e)
    {
        Browser.Dispose();
        base.OnClosed(e);
    }
}
