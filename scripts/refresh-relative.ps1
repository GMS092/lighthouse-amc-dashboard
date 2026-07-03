# Automated QuantiWise refresh -> collector -> git push for the relative-return chart.
# ASCII-only (PowerShell 5.1 reads .ps1 as ANSI; Korean literals would break).
# Flow: open Excel -> click QuantiWise "Book" (refresh workbook) -> if login form
# appears, click LOGIN (saved creds) -> if duplicate-login dialog appears, force
# login (Alt+Y) -> wait for refresh -> save -> run collector -> commit/push.
$ErrorActionPreference = "Continue"

$REPO   = "C:\Users\CHECK\Claude Code\lighthouse-amc-dashboard"
$XLSXDIR = "C:\Users\CHECK\Documents\Data"
$LOGDIR = Join-Path $REPO "logs"
$LOG    = Join-Path $LOGDIR "relative-refresh.log"
New-Item -ItemType Directory -Force -Path $LOGDIR | Out-Null
function Log($m) { $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; "$t  $m" | Tee-Object -FilePath $LOG -Append | Out-Null; Write-Output $m }

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int m);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr h, StringBuilder s, int m);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
  public static string Txt(IntPtr h){ var s=new StringBuilder(512); GetWindowText(h,s,512); return s.ToString(); }
  public static string Cls(IntPtr h){ var s=new StringBuilder(256); GetClassName(h,s,256); return s.ToString(); }
  public static List<IntPtr> Tops(){ var l=new List<IntPtr>(); EnumWindows((h,p)=>{ if(IsWindowVisible(h)) l.Add(h); return true;}, IntPtr.Zero); return l; }
  public static List<IntPtr> Kids(IntPtr par){ var l=new List<IntPtr>(); EnumChildWindows(par,(h,p)=>{ l.Add(h); return true;}, IntPtr.Zero); return l; }
}
"@

function Find-Top([string]$titlePart) {
  foreach ($h in [W]::Tops()) { if ([W]::Txt($h) -match $titlePart) { return $h } }
  return [IntPtr]::Zero
}
function Center($h) { $r = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r) | Out-Null; return @([int](($r.L+$r.R)/2), [int](($r.T+$r.B)/2), $r) }
function ClickHwnd($h) {
  $c = Center $h
  [W]::SetCursorPos($c[0], $c[1]) | Out-Null; Start-Sleep -Milliseconds 250
  [W]::mouse_event(0x02,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 90; [W]::mouse_event(0x04,0,0,0,[IntPtr]::Zero)
}

Log "==== refresh-relative start ===="
$xlsx = (Get-ChildItem (Join-Path $XLSXDIR "*.xlsx") | Select-Object -First 1).FullName
Log "xlsx: $xlsx"

$AE=[System.Windows.Automation.AutomationElement]; $TS=[System.Windows.Automation.TreeScope]; $root=$AE::RootElement
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $true; $xl.DisplayAlerts = $false
$wb = $xl.Workbooks.Open($xlsx, 0, $false)
$before = $wb.Worksheets.Item(1).Cells.Item(1,2).Value2
Log "opened. B1(before)=$before"
Start-Sleep -Seconds 3

# click QuantiWise "Book"
$win = $root.FindFirst($TS::Children,(New-Object System.Windows.Automation.PropertyCondition($AE::ClassNameProperty,"XLMAIN")))
[W]::ShowWindow([IntPtr]($win.Current.NativeWindowHandle),9) | Out-Null
[W]::SetForegroundWindow([IntPtr]($win.Current.NativeWindowHandle)) | Out-Null
Start-Sleep -Milliseconds 800
$tab = $win.FindFirst($TS::Descendants,(New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty,"Quantiwise 7G")))
$p=$tab.GetClickablePoint(); [W]::SetCursorPos([int]$p.X,[int]$p.Y)|Out-Null; Start-Sleep -Milliseconds 200
[W]::mouse_event(0x02,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 80; [W]::mouse_event(0x04,0,0,0,[IntPtr]::Zero)
Start-Sleep -Seconds 2
$book = $win.FindFirst($TS::Descendants,(New-Object System.Windows.Automation.PropertyCondition($AE::NameProperty,"Book")))
$p=$book.GetClickablePoint(); [W]::SetCursorPos([int]$p.X,[int]$p.Y)|Out-Null; Start-Sleep -Milliseconds 200
[W]::mouse_event(0x02,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 80; [W]::mouse_event(0x04,0,0,0,[IntPtr]::Zero)
Log "clicked Book (refresh)"

# handle login form (up to 30s)
$loginDone = $false
for ($i=0; $i -lt 15; $i++) {
  Start-Sleep -Seconds 2
  $lf = Find-Top "Quantiwise7_Login"
  if ($lf -ne [IntPtr]::Zero) {
    # login form picture-box buttons; leftmost = LOGIN
    $pics = @()
    foreach ($k in [W]::Kids($lf)) { if ([W]::Cls($k) -match "PictureBox") { $r=New-Object W+RECT; [W]::GetWindowRect($k,[ref]$r)|Out-Null; $pics += ,@($k,$r.L) } }
    if ($pics.Count -ge 1) {
      $login = ($pics | Sort-Object { $_[1] })[0][0]
      [W]::SetForegroundWindow($lf) | Out-Null; Start-Sleep -Milliseconds 300
      ClickHwnd $login
      Log "login form found -> clicked LOGIN button"
      $loginDone = $true
      break
    }
  }
}
if (-not $loginDone) { Log "no login form (already logged in?) - continuing" }

# handle duplicate-login confirm dialog (#32770 titled Quantiwise7G) up to 20s -> Alt+Y (force)
for ($i=0; $i -lt 10; $i++) {
  Start-Sleep -Seconds 2
  $dlg = [IntPtr]::Zero
  foreach ($h in [W]::Tops()) { if ([W]::Cls($h) -eq "#32770" -and [W]::Txt($h) -match "Quantiwise") { $dlg=$h; break } }
  if ($dlg -ne [IntPtr]::Zero) {
    [W]::SetForegroundWindow($dlg) | Out-Null; Start-Sleep -Milliseconds 400
    [System.Windows.Forms.SendKeys]::SendWait("%Y")   # Alt+Y = force login (Yes)
    Log "duplicate-login dialog -> sent Alt+Y (force login)"
    break
  }
}

# wait for refresh: B1 changes (start), then buffer for finish
$started = $false
for ($i=0; $i -lt 45; $i++) {
  Start-Sleep -Seconds 2
  try { $now = $wb.Worksheets.Item(1).Cells.Item(1,2).Value2 } catch { $now = $before }
  if ($now -and $now -ne $before) { Log "refresh started (B1=$now)"; $started = $true; break }
}
if ($started) { Log "waiting 60s for refresh to finish..."; Start-Sleep -Seconds 60 }
else { Log "B1 did not change - waiting 90s as fallback"; Start-Sleep -Seconds 90 }

# save + close
try { $wb.Save(); Log "workbook saved" } catch { Log "save error: $($_.Exception.Message)" }
try { $wb.Close($false); $xl.Quit(); Log "excel closed" } catch { Log "close error: $($_.Exception.Message)" }
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null

# collector
$env:PYTHONIOENCODING = "utf-8"
Set-Location $REPO
Log "running collector..."
& cmd /c "python modules\relative-return\collect.py >> `"$LOG`" 2>&1"
$genBase = ""
try { $genBase = (Get-Content (Join-Path $REPO "data\relative-return.json") -Raw -Encoding UTF8 | ConvertFrom-Json).base_date } catch {}
Log "collector done. base_date=$genBase"

# git commit + push
& cmd /c "git -C `"$REPO`" pull --ff-only origin main >> `"$LOG`" 2>&1"
& cmd /c "git -C `"$REPO`" add data/relative-return.json >> `"$LOG`" 2>&1"
$staged = & cmd /c "git -C `"$REPO`" diff --cached --name-only"
if ($staged) {
  & cmd /c "git -C `"$REPO`" commit -m `"chore: daily relative-return refresh (base $genBase)`" >> `"$LOG`" 2>&1"
  & cmd /c "git -C `"$REPO`" push origin main >> `"$LOG`" 2>&1"
  Log "committed + pushed"
} else {
  Log "no data change - skip commit"
}
Log "==== refresh-relative done ===="
