using System.Runtime.InteropServices.JavaScript;
using GameScripts.Survivor;
using HEngine.WebAssembly;

[assembly: System.Runtime.Versioning.SupportedOSPlatform("browser")]
public static partial class Program
{
    private static readonly GameSessionBridge<WebGameSession> sGame =
        new((catalog, save) => new WebGameSession(catalog, save));
    public static void Main() { }
    [JSExport] public static string Initialize(string catalog, string save) => sGame.Initialize(catalog, save);
    [JSExport] public static string Command(string name, string value) => sGame.Command(name, value);
    [JSExport] public static string Step(double seconds, double x, double z) => sGame.Step(seconds, x, z);
    [JSExport] public static string Save() => sGame.Save();
}
