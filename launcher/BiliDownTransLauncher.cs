using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace BiliDownTransLauncher
{
    internal static class Program
    {
        [STAThread]
        private static int Main()
        {
            string root = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string script = Path.Combine(root, "BiliDownTransLauncher.cmd");

            if (!File.Exists(script))
            {
                MessageBox.Show("找不到启动脚本：" + script, "BiliDownTrans", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }

            ProcessStartInfo startInfo = new ProcessStartInfo(script)
            {
                WorkingDirectory = root,
                UseShellExecute = true
            };

            Process.Start(startInfo);

            return 0;
        }
    }
}
