// Windows 11 / .NET Framework 4.8. No Python, Conda, Git or shell is required by students.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Runtime.InteropServices;

public static class SetupEngine
{
    public static string LastLog;
    public static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 16000000 };
    public static string Hash(string path) { using(var h=SHA256.Create()) using(var f=File.OpenRead(path)) return BitConverter.ToString(h.ComputeHash(f)).Replace("-", "").ToLowerInvariant(); }
    public static T Read<T>(string path) { return Json.Deserialize<T>(File.ReadAllText(path, Encoding.UTF8)); }
    public static Bundle ReadBundle(string folder) {
        // A changed manifest cannot approve changed payloads for the same host.
        // Publisher authentication still requires trusted/signed delivery of the host.
        using(var resource=typeof(SetupEngine).Assembly.GetManifestResourceStream("PsyCoLab.Bundle")) {
            if(resource==null)throw new IOException("This setup has no sealed package inventory. Obtain the complete reviewed package.");
            using(var reader=new StreamReader(resource,Encoding.UTF8)) {
                string expected=reader.ReadToEnd(),actual=File.ReadAllText(Path.Combine(folder,"bundle.json"),Encoding.UTF8);
                if(actual!=expected)throw new IOException("The package inventory changed. Obtain the complete reviewed package again.");
                return Json.Deserialize<Bundle>(expected);
            }
        }
    }
    public static void Save(string path, object value) {
        string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        File.WriteAllText(temp, Json.Serialize(value), new UTF8Encoding(false));
        if(File.Exists(path)) File.Replace(temp,path,null); else File.Move(temp,path);
    }
    public static string Full(string p) { string full=Path.GetFullPath(p);return full.Length==Path.GetPathRoot(full).Length?full:full.TrimEnd(Path.DirectorySeparatorChar); }
    public static bool Inside(string child,string parent) { child=Full(child);parent=Full(parent);return child.Equals(parent,StringComparison.OrdinalIgnoreCase)||child.StartsWith(parent.TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase); }
    public static void Plain(string path) {
        for(string p=Full(path);!String.IsNullOrEmpty(p);p=Path.GetDirectoryName(p))
            if((File.Exists(p)||Directory.Exists(p))&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0) throw new IOException("Linked installation folders are not supported. Choose an ordinary folder.");
    }
    public static string At(string root,string relative) {
        if(String.IsNullOrWhiteSpace(relative)||relative.Contains(":")||relative.Contains("\\")||relative.Split('/').Any(segment=>segment==".."||segment=="."||segment==""||segment.EndsWith(".")||segment.EndsWith(" ")||segment.IndexOfAny(Path.GetInvalidFileNameChars())>=0)) throw new IOException("Invalid package path.");
        string p=Full(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));Plain(p);
        if(!Inside(p,root)||p==Full(root))throw new IOException("Package path leaves its folder.");return p;
    }
    public static void Verify(string root,Dictionary<string,string> files,Func<bool> cancelled) {
        foreach(var entry in files) { if(cancelled())throw new OperationCanceledException(); string p=At(root,entry.Key);
            if(!File.Exists(p)||Hash(p)!=entry.Value)throw new IOException("A package or source file is missing or changed. Obtain the complete reviewed package again."); }
    }
    public static string Quote(string arg) {
        // CommandLineToArgvW quoting; no command shell or string substitution.
        var b=new StringBuilder("\"");int slashes=0;
        foreach(char c in arg) { if(c=='\\'){slashes++;continue;} if(c=='"'){b.Append('\\',slashes*2+1);b.Append(c);}else{b.Append('\\',slashes);b.Append(c);}slashes=0; }
        b.Append('\\',slashes*2);b.Append('"');return b.ToString();
    }
    public static ProcessStartInfo Start(string exe,IEnumerable<string> args,string cwd) {
        var p=new ProcessStartInfo(exe,String.Join(" ",args.Select(Quote))) { WorkingDirectory=cwd,UseShellExecute=false,CreateNoWindow=true };
        foreach(var key in p.EnvironmentVariables.Keys.Cast<string>().ToArray())
            if(key.StartsWith("PSYCOLAB_",StringComparison.OrdinalIgnoreCase)||key.StartsWith("PYTHON",StringComparison.OrdinalIgnoreCase)||key.StartsWith("CONDA_",StringComparison.OrdinalIgnoreCase)||key.StartsWith("MAMBA_",StringComparison.OrdinalIgnoreCase))p.EnvironmentVariables.Remove(key);
        p.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1";p.EnvironmentVariables["PIP_DISABLE_PIP_VERSION_CHECK"]="1";
        return p;
    }
    public static string[] ApplicationArguments(IEnumerable<string> args) {
        // The reviewed source root owns simulations/ and scripts/ as well as src/.
        // Keep that cwd import path; ignore ambient Python variables/user site.
        // Qualification itself still uses -I and is never weakened by this.
        return new[]{"-E","-s","-B","-m","psychophysics_lab"}.Concat(args).ToArray();
    }
    public static void Run(ProcessStartInfo info,string log,Func<bool> cancelled) {
        if(cancelled())throw new OperationCanceledException();
        info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        using(var writer=new StreamWriter(log,true,Encoding.UTF8)) using(var proc=new Process { StartInfo=info }) {
            object gate=new object();
            proc.OutputDataReceived+=(s,e)=>{if(e.Data!=null)lock(gate)writer.WriteLine(e.Data);};
            proc.ErrorDataReceived+=(s,e)=>{if(e.Data!=null)lock(gate)writer.WriteLine(e.Data);};
            proc.Start();proc.BeginOutputReadLine();proc.BeginErrorReadLine();proc.WaitForExit();
            if(proc.ExitCode!=0)throw new IOException("The approved installation could not be verified. Your previous installations are unchanged. See the setup log or contact your laboratory administrator.");
        }
        if(cancelled())throw new OperationCanceledException();
    }
    public static string Install(string bundle,string store,string config,string data,Action<string> progress,Func<bool> cancelled) {
        bundle=Full(bundle);store=Full(store);Plain(bundle);Plain(store);
        if(Inside(store,bundle)||Inside(bundle,store))throw new IOException("Choose an installation store separate from the setup package.");
        foreach(string protectedRoot in new[]{config,data}.Where(p=>!String.IsNullOrWhiteSpace(p))) {
            if(!Path.IsPathRooted(protectedRoot))throw new IOException("Select an absolute laboratory folder.");
            Plain(protectedRoot);
            if(Inside(store,protectedRoot)||Inside(protectedRoot,store))throw new IOException("Keep software, laboratory settings and data in separate folders.");
        }
        if(!String.IsNullOrWhiteSpace(config)&&!String.IsNullOrWhiteSpace(data)&&(Inside(config,data)||Inside(data,config)))throw new IOException("Settings and participant data must be separate folders.");
        string marker=Path.Combine(store,".psycolab-installations.json");Plain(marker);Plain(Path.Combine(store,"setup.lock"));
        if(File.Exists(marker)) { if(Read<Store>(marker).schema_version!=1)throw new IOException("Unsupported installation store. Choose a separate empty folder."); }
        else if(Directory.Exists(store)&&Directory.EnumerateFileSystemEntries(store).Any())throw new IOException("This folder is already in use. Choose a new empty installation store; nothing was changed.");
        progress("Checking the complete package. No existing installation will be replaced.");
        var pack=CheckPackage(bundle,cancelled);
        Directory.CreateDirectory(store);
        using(var guard=new FileStream(Path.Combine(store,"setup.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)) {
            Save(Path.Combine(store,".psycolab-installations.json"),new{schema_version=1});
            return InstallVerified(bundle,store,config,data,pack,progress,cancelled);
        }
    }
    public static Bundle CheckPackage(string bundle,Func<bool> cancelled) {
        var pack=ReadBundle(bundle);
        if(pack.schema_version!=1||pack.files==null||pack.source_files==null||pack.interpreter_files==null)throw new IOException("Unsupported installation package.");
        Verify(bundle,pack.files,cancelled);
        if(pack.source_files.Count==0||pack.interpreter_files.Length==0||pack.source_files.Any(entry=>!pack.files.ContainsKey("source/"+entry.Key)||pack.files["source/"+entry.Key]!=entry.Value)||pack.interpreter_files.Any(path=>!pack.files.ContainsKey(path))||!pack.files.ContainsKey("wheels/"+pack.wheel_probe))throw new IOException("The package inventory is inconsistent. Obtain a complete reviewed package.");
        if(pack.files["tools/conda.exe"]!="147e07937bb6509b69e9630eec6c6a281cd916c246d5fa5851a8b8f3b502f31f")throw new IOException("Unrecognised provisioning tool; obtain a reviewed setup package.");
        return pack;
    }
    static string InstallVerified(string bundle,string store,string config,string data,Bundle pack,Action<string> progress,Func<bool> cancelled) {
            string instance=Path.Combine(store,"versions",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(instance);
            string source=Path.Combine(instance,"source"),prefix=Path.Combine(instance,"python"),log=Path.Combine(instance,"setup.log");
            LastLog=log;
            Save(Path.Combine(instance,"incomplete.json"),new{schema_version=1,bundle_id=pack.id,created_utc=DateTime.UtcNow.ToString("o")});
            foreach(var entry in pack.source_files) {
                string src=At(bundle,"source/"+entry.Key),dest=At(source,entry.Key);Directory.CreateDirectory(Path.GetDirectoryName(dest));File.Copy(src,dest,false);
            }
            var explicitLines=new List<string>{"@EXPLICIT"};
            foreach(string relative in pack.interpreter_files)explicitLines.Add(new Uri(At(bundle,relative)).AbsoluteUri);
            string plan=Path.Combine(instance,"interpreter-explicit.txt");File.WriteAllLines(plan,explicitLines,new UTF8Encoding(false));
            progress("Installing the approved Python runtime separately. Your previous version is retained.");
            var create=Start(At(bundle,"tools/conda.exe"),new[]{"create","--offline","--yes","--copy","--no-default-packages","--prefix",prefix,"--file",plan},instance);
            create.EnvironmentVariables["CONDA_NO_PLUGINS"]="true";create.EnvironmentVariables["CONDA_SOLVER"]="classic";
            create.EnvironmentVariables["CONDA_REGISTER_ENVS"]="false";create.EnvironmentVariables["CONDA_OFFLINE"]="true";
            create.EnvironmentVariables["CONDA_PKGS_DIRS"]=Path.Combine(instance,"provisioner","pkgs");
            create.EnvironmentVariables["CONDA_ENVS_PATH"]=Path.Combine(instance,"provisioner","envs");
            string rc=Path.Combine(instance,"condarc.json");Save(rc,new{channels=new string[0],default_channels=new string[0],notify_outdated_conda=false});
            create.EnvironmentVariables["CONDARC"]=rc;Run(create,log,cancelled);
            progress("Installing and validating the locked PsyCoLab environment.");
            var setup=Start(Path.Combine(prefix,"python.exe"),new[]{"-I","-B",Path.Combine(source,"scripts","launcher_setup.py")},source);
            setup.EnvironmentVariables["PSYCOLAB_WHEELHOUSE"]=Path.GetDirectoryName(At(bundle,"wheels/"+pack.wheel_probe));
            setup.EnvironmentVariables["MPLCONFIGDIR"]=Path.Combine(instance,"setup-cache");Run(setup,log,cancelled);
            var record=new Installation { schema_version=1,id=Path.GetFileName(instance),label=pack.label,bundle_id=pack.id,
                source_commit=pack.source_commit,source_dirty=pack.source_dirty,profile_id=pack.profile_id,source_files=pack.source_files,config_root=config,data_root=data,created_utc=DateTime.UtcNow.ToString("o") };
            Validate(instance,record,log,cancelled);
            if(cancelled())throw new OperationCanceledException();
            File.Copy(typeof(SetupEngine).Assembly.Location,Path.Combine(instance,"PsyCoLab.exe"),false);
            Save(Path.Combine(instance,"installation.json"),record); // Only verified installations enter the launch list.
            progress("Installation verified. Use Open or create this version's shortcut. Previous versions remain available.");
            return instance;
    }
    public static Installation Load(string instance) {
        Plain(instance);var r=Read<Installation>(Path.Combine(instance,"installation.json"));
        if(r.schema_version!=1||r.id!=Path.GetFileName(Full(instance))||r.id.Length!=32||r.source_files==null||r.source_files.Count==0)throw new IOException("Installation identity is missing or changed. Use its original shortcut or install separately.");return r;
    }
    public static void Validate(string instance,Installation record,string log,Func<bool> cancelled) {
        LastLog=log;
        string source=Path.Combine(instance,"source");ValidateSource(source,record,cancelled);
        Run(Start(Path.Combine(source,".venv","Scripts","python.exe"),new[]{"-I","-B",Path.Combine(source,"scripts","launcher_setup.py"),"--check"},source),log,cancelled);
    }
    public static void ValidateSource(string source,Installation record,Func<bool> cancelled) {
        Verify(source,record.source_files,cancelled);
        // A new untracked experiment/module must not slip past the source seal.
        var pending=new Stack<string>();pending.Push(source);
        while(pending.Count>0)foreach(string path in Directory.EnumerateFileSystemEntries(pending.Pop())) {
            Plain(path);string relative=path.Substring(source.Length+1).Replace('\\','/');
            if(Directory.Exists(path)) {
                if(relative==".venv"||relative==".psycolab_logs"||relative.EndsWith(".egg-info")||relative.EndsWith("__pycache__"))continue;
                pending.Push(path);
            }else if(!record.source_files.ContainsKey(relative))throw new IOException("This installation has added or changed source files. Install a reviewed version separately; it was preserved.");
        }
    }
    public static void Launch(string instance,Func<bool> cancelled=null) {
        cancelled=cancelled??(()=>false);
        var record=Load(instance);Validate(instance,record,Path.Combine(Path.GetTempPath(),"psycolab-launch-"+Guid.NewGuid().ToString("N")+".log"),cancelled);
        if(cancelled())throw new OperationCanceledException();
        string source=Path.Combine(instance,"source");var start=Start(Path.Combine(source,".venv","Scripts","python.exe"),ApplicationArguments(new string[0]),source);start.CreateNoWindow=false;
        start.EnvironmentVariables["PSYCOLAB_CONFIG_DIR"]=String.IsNullOrWhiteSpace(record.config_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","LaboratoryConfiguration"):record.config_root;
        start.EnvironmentVariables["PSYCOLAB_DATA_DIR"]=String.IsNullOrWhiteSpace(record.data_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"PsyCoLabData"):record.data_root;
        Process.Start(start);
    }
    public static void Shortcut(string instance,string destination) {
        if(File.Exists(destination))throw new IOException("That shortcut exists. Choose another name; it was preserved.");
        dynamic shell=Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));dynamic link=shell.CreateShortcut(destination);
        link.TargetPath=Path.Combine(instance,"PsyCoLab.exe");link.Arguments="--launch "+Quote(instance);link.WorkingDirectory=instance;link.Description="PsyCoLab — "+Load(instance).label;link.Save();
    }
    public class Bundle { public int schema_version;public bool source_dirty;public string id,label,source_commit,profile_id,wheel_probe;public Dictionary<string,string> files,source_files;public string[] interpreter_files; }
    public class Store { public int schema_version; }
    public class Installation { public int schema_version;public bool source_dirty;public string id,label,bundle_id,source_commit,profile_id,config_root,data_root,created_utc;public Dictionary<string,string> source_files;public override string ToString(){return label+" — "+id.Substring(0,8);} }
}

public class SetupWindow : Form
{
    readonly string bundle;readonly TextBox store=new TextBox(),config=new TextBox(),data=new TextBox();
    readonly ListBox versions=new ListBox();readonly Label status=new Label();readonly Button install=new Button(),open=new Button(),shortcut=new Button(),cancel=new Button(),logs=new Button();
    bool busy;volatile bool stopping;readonly List<string> paths=new List<string>();readonly List<Button> browsers=new List<Button>();
    public SetupWindow(string package,string root) {
        bundle=package;Text="PsyCoLab Setup — separate installations";Width=820;Height=650;MinimumSize=new System.Drawing.Size(760,620);StartPosition=FormStartPosition.CenterScreen;
        var layout=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=12,Padding=new Padding(16)};Controls.Add(layout);
        layout.Controls.Add(new Label{Text="Private qualification candidate — not a released installer",AutoSize=true});
        layout.Controls.Add(new Label{Text="Install a reviewed version separately. Existing software, laboratory settings and data are retained.",AutoSize=true});
        if(File.Exists(Path.Combine(bundle,"bundle.json")))layout.Controls.Add(new Label{Text="Package: "+SetupEngine.Read<SetupEngine.Bundle>(Path.Combine(bundle,"bundle.json")).label,AutoSize=true});
        AddPath(layout,"Where to keep PsyCoLab versions",store,root);
        AddPath(layout,"Existing laboratory settings (optional; blank uses each student's own settings)",config,"");
        AddPath(layout,"Existing participant data (optional; blank uses each student's Documents folder)",data,"");
        layout.Controls.Add(new Label{Text="Retained installations — select one to continue or return to it:",AutoSize=true});
        versions.Dock=DockStyle.Fill;layout.Controls.Add(versions);layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        var buttons=new FlowLayoutPanel{AutoSize=true,Dock=DockStyle.Fill};layout.Controls.Add(buttons);
        install.Text="Install separately";open.Text="Open selected version";shortcut.Text="Create shortcut";cancel.Text="Cancel";logs.Text="View setup log";
        foreach(var b in new[]{install,open,shortcut,cancel,logs}){b.AutoSize=true;buttons.Controls.Add(b);}
        status.Text="Nothing will be downloaded or installed when you open an existing version.";status.AutoSize=true;status.MaximumSize=new System.Drawing.Size(740,0);layout.Controls.Add(status);
        install.Enabled=File.Exists(Path.Combine(bundle,"bundle.json"));
        install.Click+=async(s,e)=>{string destination=store.Text,settings=config.Text,records=data.Text;
            await Work(async()=>{string installed=await Task.Run(()=>SetupEngine.Install(bundle,destination,settings,records,Message,()=>stopping));RefreshVersions(installed);});};
        open.Click+=async(s,e)=>{if(versions.SelectedIndex>=0){string selected=paths[versions.SelectedIndex];Message("Checking this version before opening. No installation or update is being performed.");await Work(async()=>{await Task.Run(()=>SetupEngine.Launch(selected,()=>stopping));Message("Launch handed to this version. You can keep Setup open to choose another retained version.");});}};
        versions.SelectedIndexChanged+=(s,e)=>{if(!busy&&versions.SelectedIndex>=0){var selected=SetupEngine.Load(paths[versions.SelectedIndex]);config.Text=selected.config_root;data.Text=selected.data_root;}};
        logs.Click+=(s,e)=>{if(!String.IsNullOrWhiteSpace(SetupEngine.LastLog)&&File.Exists(SetupEngine.LastLog))Process.Start("notepad.exe",SetupEngine.Quote(SetupEngine.LastLog));else Message("No setup log yet. Logs are kept beside each installation attempt.");};
        shortcut.Click+=(s,e)=>{if(versions.SelectedIndex<0)return;using(var dialog=new SaveFileDialog{Filter="Windows shortcut|*.lnk",FileName="PsyCoLab "+SetupEngine.Load(paths[versions.SelectedIndex]).label+".lnk",InitialDirectory=Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory)})
            if(dialog.ShowDialog(this)==DialogResult.OK)try{SetupEngine.Shortcut(paths[versions.SelectedIndex],dialog.FileName);Message("Version-specific shortcut created. It will never select a newer version automatically.");}catch(Exception ex){Message(ex.Message);}};
        cancel.Click+=(s,e)=>{if(busy){stopping=true;Message("Stopping safely after the current step. Previous installations are unchanged.");}else Close();};
        FormClosing+=(s,e)=>{if(busy){e.Cancel=true;stopping=true;Message("Stopping safely after the current step. Please keep this window open.");}};
        store.Leave+=(s,e)=>RefreshVersions();RefreshVersions();
    }
    void AddPath(TableLayoutPanel layout,string label,TextBox box,string value) {
        var panel=new FlowLayoutPanel{AutoSize=true,Dock=DockStyle.Fill};panel.Controls.Add(new Label{Text=label,AutoSize=true,Width=730});box.Text=value;box.Width=650;box.AccessibleName=label;panel.Controls.Add(box);
        var browse=new Button{Text="Browse",AutoSize=true};browsers.Add(browse);panel.Controls.Add(browse);browse.Click+=(s,e)=>{using(var d=new FolderBrowserDialog{Description=label,SelectedPath=box.Text})if(d.ShowDialog(this)==DialogResult.OK){box.Text=d.SelectedPath;RefreshVersions();}};layout.Controls.Add(panel);
    }
    void Message(string value){if(InvokeRequired){BeginInvoke(new Action<string>(Message),value);return;}status.Text=value;}
    void RefreshVersions(string prefer=null) {
        if(prefer==null&&versions.SelectedIndex>=0)prefer=paths[versions.SelectedIndex];
        paths.Clear();versions.Items.Clear();string folder=Path.Combine(store.Text,"versions");if(!Directory.Exists(folder))return;
        foreach(string p in Directory.GetDirectories(folder).OrderBy(p=>p))try{var record=SetupEngine.Load(p);paths.Add(p);versions.Items.Add(record);}catch{ }
        if(versions.Items.Count>0)versions.SelectedIndex=prefer!=null&&paths.Contains(prefer)?paths.IndexOf(prefer):versions.Items.Count-1;
    }
    async Task Work(Func<Task> action) {
        busy=true;stopping=false;foreach(var c in new Control[]{install,open,shortcut,store,config,data,versions})c.Enabled=false;
        foreach(var b in browsers)b.Enabled=false;
        try{await action();}catch(OperationCanceledException){Message("Setup cancelled safely. Previous installations remain available; an incomplete attempt may be retained for diagnosis.");}
        catch(Exception ex){Message(ex.Message+" No older installation was replaced. You can continue using a retained version or cancel.");}
        finally{busy=false;foreach(var c in new Control[]{open,shortcut,store,config,data,versions})c.Enabled=true;foreach(var b in browsers)b.Enabled=true;install.Enabled=File.Exists(Path.Combine(bundle,"bundle.json"));RefreshVersions();}
    }
    [STAThread] public static int Main(string[] args) {
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        try {
            if(args.Length>=2&&args[0]=="--entry")return SourceMenu.Entry(SetupEngine.Full(args[1]),args.Skip(2).ToArray());
            if(args.Length==2&&args[0]=="--launch")return StartupRecovery.LaunchFixed(SetupEngine.Full(args[1]));
            if(args.Length>=2&&args[0]=="--source")return StartupRecovery.LaunchSource(SetupEngine.Full(args[1]),args.Skip(2).ToArray());
            if(args.Length>=2&&args[0]=="--python")return StartupRecovery.LaunchPython(SetupEngine.Full(args[1]),args.Skip(2).ToArray());
            if(args.Length==2&&args[0]=="--recover")return StartupRecovery.Recover(SetupEngine.Full(args[1]));
            if(args.Length==3&&args[0]=="--recover"&&(args[2]=="--repair"||args[2]=="--restore"))return SourceRecovery.Command(SetupEngine.Full(args[1]),args[2]=="--restore");
            string bundle=AppDomain.CurrentDomain.BaseDirectory,store=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","Installations");
            if(args.Length==4&&args[0]=="--bundle"&&args[2]=="--store"){bundle=SetupEngine.Full(args[1]);store=SetupEngine.Full(args[3]);}
            else if(args.Length!=0)throw new ArgumentException("Open PsyCoLab Setup or use a version-specific shortcut.");
            Application.Run(new SetupWindow(bundle,store));return 0;
        }catch(Exception ex){MessageBox.Show(ex.Message+"\nOpen PsyCoLab Setup to install separately or select another retained version. No automatic repair was attempted.","PsyCoLab — recovery",MessageBoxButtons.OK,MessageBoxIcon.Information);return 1;}
    }
}

// Startup only: no package resolution, qualification writes, branch changes or acquisition retry.
public static class StartupRecovery
{
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool AttachConsole(uint processId);
    delegate bool ConsoleControl(uint control);
    [DllImport("kernel32.dll")]
    static extern bool SetConsoleCtrlHandler(ConsoleControl handler, bool add);
    [DllImport("kernel32.dll")]
    static extern IntPtr GetStdHandle(int kind);
    [DllImport("kernel32.dll")]
    static extern bool SetStdHandle(int kind,IntPtr handle);
    [DllImport("kernel32.dll")]
    static extern uint GetFileType(IntPtr handle);
    static readonly ConsoleControl KeepObserver = control => control == 0 || control == 1;

    public static void UseParentConsole() {
        // This host is a winexe. Without attachment its console Python child
        // allocates another window while the double-clicked batch waits empty.
        // ERROR_ACCESS_DENIED simply means an existing console is already owned.
        // Direct GUI/shortcut launches have no parent console; Python then
        // allocates the one console it needs, as before.
        // Attachment can replace inherited redirected handles with console
        // handles. Preserve valid files/pipes so scripted input/output still work.
        var kinds=new[]{-10,-11,-12};var handles=kinds.Select(GetStdHandle).ToArray();
        var redirected=handles.Select(h=>GetFileType(h)==1||GetFileType(h)==3).ToArray();
        if(AttachConsole(unchecked((uint)-1))) {
            for(int i=0;i<kinds.Length;i++)if(redirected[i])SetStdHandle(kinds[i],handles[i]);
            SetConsoleCtrlHandler(KeepObserver,true);
        }
    }
    public class Diagnosis {
        public string category,message,details,root,original_root;
        public bool healthy,after_application,development;
    }
    public class Candidate { public string root,instance,label;public override string ToString(){return label;} }
    static Dictionary<string,object> ObjectAt(Dictionary<string,object> d,string key) {
        return d!=null&&d.ContainsKey(key)?d[key] as Dictionary<string,object>:null;
    }
    static string StringAt(Dictionary<string,object> d,string key) {
        return d!=null&&d.ContainsKey(key)?Convert.ToString(d[key]):null;
    }
    static Diagnosis Problem(string root,string category,string message,string details="") {
        return new Diagnosis{root=root,category=category,message=message,details=details};
    }
    public static string Store { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","Installations"); } }
    public static bool DeveloperCheckout(string root) {
        if(String.IsNullOrWhiteSpace(root))return false;
        return (Directory.Exists(Path.Combine(root,".git"))||File.Exists(Path.Combine(root,".git")))
            &&!File.Exists(Path.Combine(Path.GetDirectoryName(SetupEngine.Full(root)),"installation.json"))
            &&File.Exists(Path.Combine(root,"scripts","developer_setup.py"));
    }
    static bool DevelopmentSelected(string root) {
        // Never fall back from a failed, damaged or legacy laboratory environment.
        string qualified=Path.Combine(root,".venv");
        return DeveloperCheckout(root)&&!Directory.Exists(qualified)&&!File.Exists(qualified)
            &&Directory.Exists(Path.Combine(root,".venv-dev"));
    }
    public static Diagnosis Inspect(string root) {
        try {
            root=SetupEngine.Full(root);SetupEngine.Plain(root);
            if(DevelopmentSelected(root)) {
                string env=Path.Combine(root,".venv-dev");SetupEngine.Plain(env);
                SetupEngine.Plain(Path.Combine(env,".psycolab-development.json"));
                SetupEngine.Plain(Path.Combine(env,"Scripts","python.exe"));
                if(!File.Exists(Path.Combine(env,"Scripts","python.exe")))return Problem(root,"development_environment_missing","The maintainer environment is incomplete. Open PsyCoLab.bat and choose 2 - Check / Repair PsyCoLab.");
                return new Diagnosis{root=root,category="check_required",development=true,message="Maintainer development checkout; read-only checks are still required. No laboratory qualification is claimed."};
            }
            string python=Path.Combine(root,".venv","Scripts","python.exe"),statePath=Path.Combine(root,".venv",".psycolab-setup.json");
            SetupEngine.Plain(python);SetupEngine.Plain(statePath);
            string project=Path.Combine(root,"pyproject.toml"),profilePath=Path.Combine(root,"requirements","windows-cp311","profile.json");
            if(!File.Exists(project)||!File.Exists(profilePath)||!File.Exists(Path.Combine(root,"scripts","launcher_setup.py")))
                return Problem(root,"source_missing","Required PsyCoLab source or profile files are missing or inaccessible. Ask the administrator to check the reviewed checkout path and permissions.");
            var profile=SetupEngine.Read<Dictionary<string,object>>(profilePath);
            var profileFiles=ObjectAt(profile,"files");
            if(profileFiles==null) return Problem(root,"profile_invalid","The dependency profile cannot be verified. It has not been approved by this launcher.");
            foreach(var file in profileFiles) {
                string path=SetupEngine.At(Path.GetDirectoryName(profilePath),file.Key);
                if(!File.Exists(path)||SetupEngine.Hash(path)!=Convert.ToString(file.Value))return Problem(root,"profile_invalid","A dependency-profile file is missing or changed. Keep this installation and obtain administrator guidance.");
            }
            if(!File.Exists(statePath)&&File.Exists(Path.Combine(root,".venv",".psycolab-setup.pending.json")))
                return Problem(root,"setup_interrupted","Installation was interrupted before qualification completed. This attempt will not be resumed or approved during launch.");
            if(!File.Exists(python))return Problem(root,"environment_missing","This checkout's Python environment is missing or damaged. No other Python environment will be selected.");
            if(!File.Exists(statePath))return Problem(root,"qualification_missing","This environment has no qualification record. Its compatibility cannot safely be inferred from installed packages alone.");
            var state=SetupEngine.Read<Dictionary<string,object>>(statePath);var qualification=ObjectAt(state,"qualification");
            if(StringAt(state,"schema_version")!="2"||qualification==null)
                return Problem(root,"qualification_legacy","This environment has an older or incomplete qualification record. Launch will not rewrite it or approve it automatically.");
            string original=StringAt(state,"source_root");
            if(String.IsNullOrWhiteSpace(original)||!String.Equals(SetupEngine.Full(original),root,StringComparison.OrdinalIgnoreCase)) {
                var d=Problem(root,"installation_path_changed","This environment belongs to a different checkout location. Moving or copying an environment does not requalify it.");d.original_root=original;return d;
            }
            if(StringAt(qualification,"profile_sha256")!=SetupEngine.Hash(profilePath))
                return Problem(root,"profile_changed","The selected branch or checkout declares a different interpreter/dependency profile from this environment's qualification.");
            if(StringAt(state,"pyproject_sha256")!=SetupEngine.Hash(project))
                return Problem(root,"requirements_changed","This source revision has a different dependency specification. The existing environment was preserved.");
            return new Diagnosis{root=root,category="check_required",message="Source location and declared environment agree; installed-file checks are still required."};
        } catch(Exception error) { return Problem(root,"evidence_unreadable","Startup evidence could not be read safely. No correction was attempted.",error.Message); }
    }
    public static ProcessStartInfo SourceProcess(string root,IEnumerable<string> args,bool development=false) {
        var start=SetupEngine.Start(Path.Combine(root,development?".venv-dev":".venv","Scripts","python.exe"),args,root);
        // Existing explicit laboratory roots remain authoritative for a source checkout.
        foreach(string key in new[]{"PSYCOLAB_CONFIG_DIR","PSYCOLAB_DATA_DIR"}) {
            string value=Environment.GetEnvironmentVariable(key);if(!String.IsNullOrWhiteSpace(value))start.EnvironmentVariables[key]=value;
        }
        start.EnvironmentVariables["PSYCOLAB_LAUNCH_ROLE"]="unknown";
        start.EnvironmentVariables["PSYCOLAB_REPO_ROOT"]=root;return start;
    }
    public static Diagnosis Diagnose(string root) {
        var d=Inspect(root);if(d.category!="check_required")return d;
        try {
            // A packaged source also retains its existing complete source seal.
            string instance=Path.GetDirectoryName(root);
            if(File.Exists(Path.Combine(instance,"installation.json"))) {
                string source=Path.Combine(instance,"source");
                if(!String.Equals(SetupEngine.Full(source),SetupEngine.Full(root),StringComparison.OrdinalIgnoreCase))throw new IOException("Unexpected installation layout.");
                SetupEngine.ValidateSource(root,SetupEngine.Load(instance),()=>false);
            }
            var start=SourceProcess(root,new[]{"-I","-B",Path.Combine(root,"scripts",d.development?"developer_setup.py":"launcher_setup.py"),"--check"},d.development);
            start.RedirectStandardOutput=true;start.RedirectStandardError=true;
            using(var p=Process.Start(start)) {
                var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();p.WaitForExit();
                d.details=output.Result+error.Result;
                if(p.ExitCode!=0)return Problem(root,d.development?"development_check_failed":"qualification_check_failed",d.development?"The maintainer development check failed. Open PsyCoLab.bat and choose 2 - Check / Repair PsyCoLab; ordinary startup does not repair environments.":"The existing read-only qualification check failed. This may concern installed files, interpreter or editable-source identity; see the diagnostic evidence.",d.details);
            }
            d.healthy=true;d.category="healthy";d.message=d.development?"Maintainer development checks passed. This environment has no locked laboratory qualification.":"This checkout passed its existing read-only qualification checks. No installation, repair or requalification was performed.";
        }catch(Exception error){return Problem(root,"environment_or_source_damaged","This installation could not pass its existing source/environment checks. Nothing was repaired.",error.Message);}
        return d;
    }
    public static List<Candidate> Retained(Diagnosis failure,string store) {
        var result=new List<Candidate>();if(failure.healthy||failure.after_application)return result;
        if(!String.IsNullOrWhiteSpace(failure.original_root)&&Directory.Exists(failure.original_root)) {
            var original=Diagnose(failure.original_root);if(original.healthy&&!original.development)result.Add(new Candidate{root=original.root,label="Verified original checkout: "+original.root});
        }
        string versions=Path.Combine(store,"versions");string[] entries;
        try{entries=Directory.Exists(versions)?Directory.GetDirectories(versions):new string[0];}
        catch(Exception error){failure.details+="; retained store could not be inspected: "+error.Message;return result;}
        foreach(string instance in entries)try {
            SetupEngine.Plain(instance);var record=SetupEngine.Load(instance);
            // The source seal and existing read-only gate both pass before offering it.
            string source=Path.Combine(instance,"source");
            SetupEngine.ValidateSource(source,record,()=>false);
            if(Diagnose(source).healthy)result.Add(new Candidate{root=source,instance=instance,label=record.ToString()});
        }catch { /* Unverified entries are not launch choices. */ }
        return result;
    }
    public static bool PackageAvailable(string folder) {
        try{SetupEngine.CheckPackage(folder,()=>false);return true;}catch{return false;}
    }
    public static string Recommendation(Diagnosis d,int retained,bool package) {
        if(d.healthy)return "cancel";
        if(!d.after_application&&SourceRecovery.CanRepair(d.root))return "repair";
        if(!d.after_application&&retained>0)return "retained";
        if(!d.after_application&&package)return "separate";
        return "diagnostics";
    }
    public static string Reason(string option) {
        if(option=="repair")return "This source installation has a supported repair. Recovery preserves the older environment, prepares pinned source dependencies and verifies startup before opening PsyCoLab.";
        if(option=="cancel")return "The installation already passes its checks. Close recovery and use PsyCoLab.bat, option 1, for ordinary launch.";
        if(option=="retained")return "A retained installation has already passed its existing read-only checks. Using it preserves the failing checkout and all its evidence.";
        if(option=="separate")return "This host's sealed package and every required artifact verified. The existing guided setup can create a separate installation without replacing this one.";
        return "No automatic correction has been established for this failure. Diagnostics give the administrator the verified evidence without changing this installation.";
    }
    public static string Instructions(Diagnosis d) {
        string common="Preserve the source, environment, qualification records, calibration and data. Never edit a qualification record, install dependencies in place or repeat acquisition automatically. ";
        if(d.after_application)return common+"Inspect the application's existing crash/fatal and incomplete-run records. The exit phase is diagnostic evidence, not authority to resume or repeat an experiment.";
        if(SourceRecovery.CanRepair(d.root))return common+SourceRecovery.Explanation;
        if(DeveloperCheckout(d.root)&&!Directory.Exists(Path.Combine(d.root,".venv")))return common+"For this maintainer checkout, open PsyCoLab.bat and choose 2 - Check / Repair PsyCoLab with installed 64-bit CPython 3.11, then choose 1 - Launch PsyCoLab. This creates a separate .venv-dev and does not grant laboratory qualification. For laboratory deployment use the approved environment guide in docs/WINDOWS_ENVIRONMENT.md.";
        if(d.category.StartsWith("qualification_"))return common+"Have the administrator review .venv/.psycolab-setup.json and the captured read-only check output. Missing or older records are not proof that installed packages are qualified. Obtain a separate approved installation if qualification cannot be established.";
        if(d.category=="installation_path_changed")return common+"Use the original checkout only if it still passes the existing checks. Do not copy an environment or its qualification evidence into another source path.";
        if(d.category.StartsWith("profile_")||d.category=="requirements_changed")return common+"Compare this revision's pyproject.toml and requirements/windows-cp311 profile with the recorded profile. Compatible scientific-source edits do not by themselves require dependency repair; a changed dependency contract needs a separately approved environment.";
        if(d.category=="setup_interrupted")return common+"Retain the pending attempt and its setup log. Ordinary launch does not resume provisioning. Use the existing guided installer with a complete verified package to create a separate installation.";
        return common+"Ask the administrator to check this checkout's path/access and reviewed launcher files. A separate installation requires the complete sealed package, not loose wheels or an arbitrary Python environment. See docs/STARTUP_RECOVERY.md.";
    }
    public static Diagnosis Incident(string root,int code,string phase) {
        string category=phase=="application_startup"?"application_startup_failure":
            new[]{"post_tui_experiment_launch","synthetic_simulation","uncalibrated_presentation_test","finished"}.Contains(phase)?"experiment_or_operation_failure":"unknown_application_exit";
        return new Diagnosis{root=root,category=category,after_application=true,message=category=="application_startup_failure"?
            "PsyCoLab stopped during application startup. See diagnostics for the reported error. No restart or repair has been attempted.":
            "PsyCoLab stopped after launch. An experiment may have begun; preserve incomplete runs and use the existing incident reports. No experimental operation will be retried.",details="Exit code: "+code+"; reported application phase: "+(phase??"unavailable")};
    }
    static int Observe(ProcessStartInfo start,string root,bool splash=false) {
        string phase=null,applicationReport=null;
        // One exit notification over a private OS pipe; no marker in source or data.
        string name="PsyCoLabStartup-"+Guid.NewGuid().ToString("N");
        using(var pipe=new System.IO.Pipes.NamedPipeServerStream(name,System.IO.Pipes.PipeDirection.In,1,System.IO.Pipes.PipeTransmissionMode.Byte,System.IO.Pipes.PipeOptions.Asynchronous)) {
            var read=Task.Run(()=>{try{pipe.WaitForConnection();using(var reader=new StreamReader(pipe,Encoding.UTF8)){var notice=SetupEngine.Json.Deserialize<ExitNotice>(reader.ReadLine());phase=notice.phase;applicationReport=notice.report;}}catch(Exception){ /* Missing or malformed evidence remains unknown. */ }});
            UseParentConsole();
            start.EnvironmentVariables["PSYCOLAB_STARTUP_PIPE"]=name;start.CreateNoWindow=false;
            int code;bool started=false;
            try {
                using(var intro=splash?StartupSplash.Begin():null) {
                    if(intro!=null)start.EnvironmentVariables["PSYCOLAB_STARTUP_HANDOFF"]=intro.Skipped?"skip":"reveal";
                    using(var child=Process.Start(start)){started=true;child.WaitForExit();code=child.ExitCode;}
                }
            }
            catch(Exception error){var failed=Problem(root,"application_start_failed",started?"Application completion could not be observed. An experiment may still be running; do not retry it.":"Windows could not start the verified application. See diagnostics.",error.Message);failed.after_application=started;Show(failed);return 1;}
            if(code==0||code==75||code==130)return code;
            // A late/missing notification is conservatively an unknown incident.
            read.Wait(250);var incident=Incident(root,code,phase);incident.details+="; application crash report: "+(applicationReport??"not reported");Show(incident);return code;
        }
    }
    public class ExitNotice { public string phase,report; }
    public static int LaunchSource(string root,string[] args) {
        Diagnosis d;
        using(var lease=SourceRecovery.Acquire(root)) {
            d=Diagnose(root);if(d.healthy)return LaunchChecked(root,args,d);
        }
        return Show(d);
    }
    public static int LaunchChecked(string root,string[] args,Diagnosis d,bool splash=false) {
        var start=SourceProcess(root,SetupEngine.ApplicationArguments(args),d.development);
        start.EnvironmentVariables["PSYCOLAB_LAUNCH_ROLE"]=d.development?"development":"locked";
        return Observe(start,root,splash);
    }
    public static int LaunchPython(string root,string[] args) {
        Diagnosis d;
        using(var lease=SourceRecovery.Acquire(root)) {
            d=Diagnose(root);if(d.healthy)return LaunchPythonChecked(root,args,d);
        }
        return Show(d);
    }
    static int LaunchPythonChecked(string root,string[] args,Diagnosis d) {
        var start=SourceProcess(root,args.Length==0?new[]{"-E","-s","-B","-i"}:
            new[]{"-E","-s","-B"}.Concat(args),d.development);
        start.EnvironmentVariables["PSYCOLAB_LAUNCH_ROLE"]=d.development?"development":"locked";
        UseParentConsole();start.CreateNoWindow=false;
        // Researcher scripts own their exit code, rather than the application's
        // crash protocol. They run once, with the verified application's Python.
        using(var child=Process.Start(start)){child.WaitForExit();return child.ExitCode;}
    }
    public static int LaunchFixed(string instance) {
        try {
            var record=SetupEngine.Load(instance);string root=Path.Combine(instance,"source");
            // Full packaged-source enumeration remains authoritative, including added files.
            SetupEngine.Validate(instance,record,Path.Combine(Path.GetTempPath(),"psycolab-fixed-check-"+Guid.NewGuid().ToString("N")+".log"),()=>false);
            var start=SourceProcess(root,SetupEngine.ApplicationArguments(new string[0]));
            start.EnvironmentVariables["PSYCOLAB_LAUNCH_ROLE"]="locked";
            start.EnvironmentVariables["PSYCOLAB_CONFIG_DIR"]=String.IsNullOrWhiteSpace(record.config_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","LaboratoryConfiguration"):record.config_root;
            start.EnvironmentVariables["PSYCOLAB_DATA_DIR"]=String.IsNullOrWhiteSpace(record.data_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"PsyCoLabData"):record.data_root;
            return Observe(start,root);
        }catch(Exception error){Show(Problem(instance,"fixed_installation_failed","This fixed-version installation failed validation. Its identity and files were preserved.",error.Message));return 1;}
    }
    public static int Recover(string root) {Diagnosis d;using(var lease=SourceRecovery.Acquire(root))d=Diagnose(root);return Show(d);}
    public static int Show(Diagnosis d) {
        using(var window=new RecoveryWindow(d,Retained(d,Store),AppDomain.CurrentDomain.BaseDirectory)){window.ShowDialog();return window.Result;}
    }
}

// Explicit source recovery only. Qualification and the managed installer are never edited.
public static class SourceRecovery
{
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
    static extern uint GetLongPathName(string shortPath,StringBuilder longPath,uint length);
    static string CanonicalSource(string path) {
        path=SetupEngine.Full(path);SetupEngine.Plain(path);
        var expanded=new StringBuilder(32768);
        uint length=GetLongPathName(path,expanded,(uint)expanded.Capacity);
        if(length==0||length>=expanded.Capacity)throw new IOException("The source folder could not be identified safely. Check its location and access.");
        return SetupEngine.Full(expanded.ToString());
    }
    static bool SameSource(string first,string second) {
        return String.Equals(CanonicalSource(first),CanonicalSource(second),StringComparison.OrdinalIgnoreCase);
    }
    public const string Explanation="Source setup preserves an older .venv in a uniquely named backup when present and prepares .venv-dev using this checkout's pinned dependencies. Source files, calibration, results and qualification records are not rewritten. Internet access or a complete reviewed wheel folder is needed. This is a source installation, not laboratory qualification. You can retry from PsyCoLab.bat, option 2, or restore a recorded backup with PsyCoLab.bat --restore. No experiment is started by setup.";
    public class Journal {
        public int schema_version=1;
        public string root,backup,record_sha256,phase,development_backup;
    }
    sealed class Lease : IDisposable {
        readonly System.Threading.Mutex mutex;
        public Lease(System.Threading.Mutex value){mutex=value;}
        public void Dispose(){mutex.ReleaseMutex();mutex.Dispose();}
    }
    public static IDisposable Acquire(string root) {
        root=CanonicalSource(root);
        string key;
        using(var hash=SHA256.Create())key=BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(root.ToUpperInvariant()))).Replace("-","");
        // An OS mutex spans sessions, leaves no source files and is released by
        // Windows after a crash. All callers retain ownership on the same thread.
        var mutex=new System.Threading.Mutex(false,"Global\\PsyCoLabSource-"+key);
        bool owned=false;
        try{try{owned=mutex.WaitOne(0);}catch(System.Threading.AbandonedMutexException){owned=true;}
            if(!owned)throw new IOException("PsyCoLab or recovery is already running for this source folder. Close it before retrying; no process will be stopped automatically.");
            return new Lease(mutex);
        }catch{mutex.Dispose();throw;}
    }
    static string StatePath(string root) {return Path.Combine(root,".psycolab-recovery","state.json");}
    static Journal ReadJournal(string root) {
        string path=StatePath(root);SetupEngine.Plain(path);
        if(!File.Exists(path))return null;
        var j=SetupEngine.Read<Journal>(path);
        if(j.schema_version!=1||!SameSource(j.root,root)||!new[]{"prepared","setup","verified","restoring","restored"}.Contains(j.phase))throw new IOException("Recovery record does not belong to this folder. Preserve it for review.");
        if(j.backup!=null)Backup(root,j.backup,".venv-recovery-backup-");
        if(j.development_backup!=null)Backup(root,j.development_backup,".venv-dev-recovery-backup-");
        return j;
    }
    static string Backup(string root,string name,string prefix) {
        Guid identity;
        if(!name.StartsWith(prefix)||!Guid.TryParseExact(name.Substring(prefix.Length),"N",out identity))throw new IOException("Invalid recovery backup location.");
        return SetupEngine.At(root,name);
    }
    static void Save(string root,Journal j) {SetupEngine.Save(StatePath(root),j);}
    static void SourceOnly(string root) {
        SetupEngine.Plain(root);
        if(!StartupRecovery.DeveloperCheckout(root)||File.Exists(Path.Combine(root,"installation.json")))throw new IOException("Repair is available only for an ordinary Git source checkout. Managed laboratory installations cannot be converted.");
        foreach(string part in new[]{".git",".venv",".venv-dev","scripts/developer_setup.py",".psycolab-recovery"})SetupEngine.Plain(Path.Combine(root,part));
        foreach(string part in new[]{"pyproject.toml","scripts/developer_setup.py","scripts/launcher_setup.py","requirements/windows-cp311/build.lock","requirements/windows-cp311/runtime.lock","requirements/windows-cp311/development.lock"})
            if(!File.Exists(Path.Combine(root,part)))throw new IOException("Required source setup files are missing. Obtain the reviewed source update before recovery; no Git update is performed automatically.");
    }
    static bool OwnedDevelopment(string root) {
        string env=Path.Combine(root,".venv-dev");
        if(File.Exists(Path.Combine(env,".psycolab-setup.json"))||File.Exists(Path.Combine(env,".psycolab-setup.pending.json")))return false;
        foreach(string name in new[]{".psycolab-development.json",".psycolab-development.pending.json"}) {
            string path=Path.Combine(env,name);SetupEngine.Plain(path);
            if(!File.Exists(path))continue;
            var s=SetupEngine.Read<Dictionary<string,object>>(path);
            if(s.ContainsKey("qualification"))return false;
            return s.ContainsKey("schema_version")&&Convert.ToString(s["schema_version"])=="1"&&s.ContainsKey("mode")&&Convert.ToString(s["mode"])=="development"&&s.ContainsKey("source_root")&&SameSource(Convert.ToString(s["source_root"]),root);
        }
        return false;
    }
    static string LegacyRecord(string root) {
        return LegacyRecordAt(Path.Combine(root,".venv"));
    }
    static string LegacyRecordAt(string env) {
        string path=Path.Combine(env,".psycolab-setup.json");
        SetupEngine.Plain(path);
        if(File.Exists(Path.Combine(env,".psycolab-setup.pending.json")))throw new IOException("An interrupted qualification attempt needs separate review; it is not a legacy source repair.");
        var s=SetupEngine.Read<Dictionary<string,object>>(path);
        // Only the historical source-setup shape is recognised. Incomplete modern
        // qualification, unknown fields and evidence from another path are refused.
        var keys=new[]{"pyproject_sha256","python","updated_utc","schema_version"};
        if(s.Keys.Any(k=>!keys.Contains(k))||!s.ContainsKey("pyproject_sha256")||!s.ContainsKey("python")||Convert.ToString(s["python"])!="3.11"||
           (s.ContainsKey("schema_version")&&Convert.ToString(s["schema_version"])!="1"))throw new IOException("This is not a recognised older source setup record. No qualification evidence will be converted or rewritten.");
        string digest=Convert.ToString(s["pyproject_sha256"]);
        if(digest.Length!=64||digest.Any(c=>!Uri.IsHexDigit(c)))throw new IOException("The older source record is incomplete; preserve it for review.");
        return SetupEngine.Hash(path);
    }
    public static bool CanRepair(string root) {
        try {
            SourceOnly(root);var j=ReadJournal(root);
            if(j!=null&&new[]{"prepared","setup"}.Contains(j.phase))return true;
            if(Directory.Exists(Path.Combine(root,".venv"))) {LegacyRecord(root);return !Directory.Exists(Path.Combine(root,".venv-dev"))||OwnedDevelopment(root);}
            return OwnedDevelopment(root);
        }catch{return false;}
    }
    public static bool CanInstall(string root) {
        try{SourceOnly(root);return ReadJournal(root)==null&&!Directory.Exists(Path.Combine(root,".venv"))&&!File.Exists(Path.Combine(root,".venv"))&&!Directory.Exists(Path.Combine(root,".venv-dev"))&&!File.Exists(Path.Combine(root,".venv-dev"));}
        catch{return false;}
    }
    public static string AvailablePython(string root) {return Python(root);}
    public static bool CanRestore(string root) {
        try{SourceOnly(root);var j=ReadJournal(root);return j!=null&&j.backup!=null&&j.phase!="restored";}
        catch{return false;}
    }
    static string Probe(string root,string exe,IEnumerable<string> prefix) {
        try {
            string code="import json,struct,sys;assert sys.implementation.name=='cpython' and sys.version_info[:2]==(3,11) and struct.calcsize('P')==8;print(json.dumps(sys._base_executable))";
            var start=SetupEngine.Start(exe,prefix.Concat(new[]{"-I","-B","-c",code}),root);
            start.EnvironmentVariables["PYMANAGER_AUTOMATIC_INSTALL"]="false";
            start.RedirectStandardOutput=true;start.RedirectStandardError=true;
            using(var p=Process.Start(start)) {
                var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();
                if(!p.WaitForExit(15000)){p.Kill();return null;}
                if(p.ExitCode!=0)return null;
                string path=SetupEngine.Json.Deserialize<string>(output.Result.Trim());SetupEngine.Plain(path);
                return File.Exists(path)&&!SetupEngine.Inside(path,root)?path:null;
            }
        }catch{return null;}
    }
    static string Python(string root) {
        string configured=Environment.GetEnvironmentVariable("PSYCOLAB_BOOTSTRAP_PYTHON");
        string found=!String.IsNullOrWhiteSpace(configured)?Probe(root,configured,new string[0]):
            (Probe(root,"py.exe",new[]{"-3.11"})??Probe(root,"python.exe",new string[0]));
        if(found==null)throw new IOException("Install 64-bit Python 3.11 (for example: py install 3.11), then run recovery again. No environment has been moved.");
        return found;
    }
    static void Idle(string root) {
        // Also detect researchers who started Python directly, outside our lease.
        // WMI is part of Windows and needs no administrator installation.
        try {
            dynamic locator=Activator.CreateInstance(Type.GetTypeFromProgID("WbemScripting.SWbemLocator"));
            dynamic service=locator.ConnectServer(".","root\\cimv2");
            foreach(dynamic p in service.ExecQuery("SELECT ProcessId,Name,ExecutablePath,CommandLine FROM Win32_Process WHERE Name LIKE 'python%'") ) {
                string exe=(string)p.ExecutablePath,cmd=(string)p.CommandLine;
                bool sourceScript=!String.IsNullOrEmpty(cmd)&&(cmd.IndexOf(Path.Combine(root,"scripts","developer_setup.py"),StringComparison.OrdinalIgnoreCase)>=0||cmd.IndexOf(Path.Combine(root,"src","psychophysics_lab"),StringComparison.OrdinalIgnoreCase)>=0);
                if((!String.IsNullOrEmpty(exe)&&SetupEngine.Inside(exe,root))||sourceScript)
                    throw new IOException("Python is running from this source folder. Close PsyCoLab and any researcher scripts before recovery. Nothing was stopped.");
            }
        }catch(IOException){throw;}
        catch(Exception error){throw new IOException("Windows could not verify that this installation is idle. No repair was started.",error);}
    }
    static void Run(string root,string python,IEnumerable<string> args,string log) {
        var start=SetupEngine.Start(python,args,root);
        string wheels=Environment.GetEnvironmentVariable("PSYCOLAB_WHEELHOUSE");
        if(!String.IsNullOrWhiteSpace(wheels))start.EnvironmentVariables["PSYCOLAB_WHEELHOUSE"]=wheels;
        start.RedirectStandardOutput=true;start.RedirectStandardError=true;
        using(var writer=new StreamWriter(log,true,Encoding.UTF8))using(var p=new Process{StartInfo=start}) {
            object gate=new object();
            writer.WriteLine("Starting process: "+python+" "+String.Join(" ",args.Select(SetupEngine.Quote)));writer.Flush();
            DataReceivedEventHandler output=(s,e)=>{if(e.Data!=null)lock(gate){writer.WriteLine(e.Data);writer.Flush();Console.WriteLine(e.Data);}};
            p.OutputDataReceived+=output;p.ErrorDataReceived+=output;
            p.Start();p.BeginOutputReadLine();p.BeginErrorReadLine();p.WaitForExit();
            if(p.ExitCode!=0) {
                string failure="Setup or verification failed (exit code "+p.ExitCode+", 0x"+p.ExitCode.ToString("X8")+").";
                writer.WriteLine(failure);writer.Flush();
                throw new IOException(failure+" The old environment is preserved. Run recovery again to retry. Report: "+log);
            }
        }
    }
    static void VerifyBackup(string root,Journal j) {
        string path=Path.Combine(Backup(root,j.backup,".venv-recovery-backup-"),".psycolab-setup.json");SetupEngine.Plain(path);
        if(!File.Exists(path)||LegacyRecordAt(Path.GetDirectoryName(path))!=j.record_sha256)throw new IOException("The preserved environment record changed or is missing. Recovery stopped without replacing it.");
    }
    public static int Execute(string root,bool restore,bool launch=true) {
        root=CanonicalSource(root);StartupRecovery.UseParentConsole();
        using(var lease=Acquire(root)) {
            SourceOnly(root);Idle(root);var j=ReadJournal(root);
            string dev=Path.Combine(root,".venv-dev");
            // Handle termination between mkdir and the setup ownership marker.
            // Only an empty directory belonging to this recorded attempt qualifies.
            if(j!=null&&j.phase=="setup"&&Directory.Exists(dev)&&Directory.GetFileSystemEntries(dev).Length==0)
                SetupEngine.Save(Path.Combine(dev,".psycolab-development.pending.json"),new{schema_version=1,mode="development",source_root=root});
            if(restore)return Restore(root,j);
            if(j!=null&&j.phase=="restoring")throw new IOException("Restoration was interrupted. Run PsyCoLab.bat --restore again.");
            if(Directory.Exists(Path.Combine(root,".venv")))LegacyRecord(root);
            if(Directory.Exists(Path.Combine(root,".venv-dev"))&&!OwnedDevelopment(root))throw new IOException("An unrelated .venv-dev already exists. It will not be adopted or overwritten.");
            if(!CanRepair(root)&&!CanInstall(root))throw new IOException("No supported source repair is available for this installation. Its files were preserved.");
            // Resolve a real base interpreter before moving the old environment.
            string python=Python(root);
            string folder=Path.GetDirectoryName(StatePath(root));Directory.CreateDirectory(folder);
            string probe=Path.Combine(root,".psycolab-recovery-write-"+Guid.NewGuid().ToString("N")+".tmp");
            using(new FileStream(probe,FileMode.CreateNew,FileAccess.Write,FileShare.None)){}File.Delete(probe);
            if(j==null||j.phase=="restored") {
                j=new Journal{root=root,phase="prepared"};
                if(Directory.Exists(Path.Combine(root,".venv"))) {j.backup=".venv-recovery-backup-"+Guid.NewGuid().ToString("N");j.record_sha256=LegacyRecord(root);}
                Save(root,j);
            }
            if(j.backup!=null) {
                string old=Path.Combine(root,".venv"),backup=Backup(root,j.backup,".venv-recovery-backup-");
                if(Directory.Exists(old)) {
                    if(j.phase!="prepared"||Directory.Exists(backup)||LegacyRecord(root)!=j.record_sha256)throw new IOException("The source environment changed since recovery began. No environment was overwritten.");
                    Directory.Move(old,backup);
                }
                VerifyBackup(root,j);
            }
            // A successful repeated invocation does not reinstall dependencies.
            var diagnosis=StartupRecovery.Diagnose(root);
            if(!diagnosis.healthy) {
                j.phase="setup";Save(root,j);
                string log=Path.Combine(folder,"repair.log");
                Console.WriteLine("Preparing source environment. Progress and report: "+log);
                Run(root,python,new[]{"-I","-B","-X","faulthandler",Path.Combine(root,"scripts","developer_setup.py"),"--repair"},log);
                diagnosis=StartupRecovery.Diagnose(root);
                if(!diagnosis.healthy||!diagnosis.development)throw new IOException("The replacement source environment did not pass startup checks. Preserve repair.log and retry recovery.");
            }
            if(j.phase!="verified")Run(root,Path.Combine(root,".venv-dev","Scripts","python.exe"),new[]{"-I","-B","-X","faulthandler","-m","psychophysics_lab","--help"},Path.Combine(folder,"repair.log"));
            j.phase="verified";Save(root,j);
            Console.WriteLine("Source installation verified. Existing backups remain available.");
            if(!launch)return 0;
            return StartupRecovery.LaunchChecked(root,new string[0],diagnosis);
        }
    }
    static int Restore(string root,Journal j) {
        if(j==null||j.backup==null)throw new IOException("No legacy environment backup is recorded for this folder.");
        if(j.phase=="restored") {Console.WriteLine("The preserved environment has already been restored. No files were changed.");return 0;}
        string old=Path.Combine(root,".venv"),backup=Backup(root,j.backup,".venv-recovery-backup-");
        if(Directory.Exists(old)) {
            if(j.phase!="prepared"&&j.phase!="restoring")throw new IOException("A .venv already exists. Restore will not overwrite it.");
            if(Directory.Exists(backup)||LegacyRecord(root)!=j.record_sha256)throw new IOException("The original environment cannot be identified safely.");
            j.phase="restored";Save(root,j);return 0;
        }
        VerifyBackup(root,j);
        j.phase="restoring";
        if(j.development_backup==null)j.development_backup=".venv-dev-recovery-backup-"+Guid.NewGuid().ToString("N");
        Save(root,j);
        string development=Path.Combine(root,".venv-dev"),retained=Backup(root,j.development_backup,".venv-dev-recovery-backup-");
        if(Directory.Exists(development)) {
            if(!OwnedDevelopment(root)||Directory.Exists(retained))throw new IOException("The development environment cannot be preserved safely. Restore stopped without overwriting it.");
            Directory.Move(development,retained);
        }
        Directory.Move(backup,old);j.phase="restored";Save(root,j);
        Console.WriteLine("Original .venv restored to its original location. The replacement is preserved separately. Legacy qualification was not repaired or approved; the old startup restriction still applies.");return 0;
    }
    public static int Command(string root,bool restore,bool launch=true) {
        try{Console.WriteLine(Explanation);return Execute(root,restore,launch);}
        catch(Exception error){StartupRecovery.UseParentConsole();Console.WriteLine(error.Message);return 1;}
    }
}

// Python-independent text entry point. Reuses the same checks, repair and observer.
public static class SourceMenu
{
    static Stream input;
    static string Answer() {
        // Read one line without prefetching commands intended for the workspace.
        if(input==null)input=Console.OpenStandardInput();
        var bytes=new List<byte>();int b;
        while((b=input.ReadByte())!=-1){if(b==10)break;if(b!=13)bytes.Add((byte)b);}
        return b==-1&&bytes.Count==0?null:Console.InputEncoding.GetString(bytes.ToArray());
    }
    public static int Entry(string root,string[] args) {
        StartupRecovery.UseParentConsole();
        try {
            if(args.Length==0)return Menu(root);
            if(args[0]=="--launch")return Launch(root,args.Skip(1).ToArray());
            if(args[0]=="--check"&&args.Length==1)return Check(root);
            if(args[0]=="--repair"&&args.Length==1)return SourceRecovery.Command(root,false,false);
            if(args[0]=="--restore"&&args.Length==1)return SourceRecovery.Command(root,true,false);
            if(args[0]=="--workspace"&&args.Length==1)return Workspace(root);
            if(args[0]=="--python")return StartupRecovery.LaunchPython(root,args.Skip(1).ToArray());
            Console.WriteLine("Usage: PsyCoLab.bat [--launch [application arguments] | --check | --repair | --restore | --workspace | --python [script and arguments]]");return 2;
        }catch(Exception error){Console.WriteLine("PsyCoLab: "+error.Message);return 1;}
    }
    static int Menu(string root) {
        for(;;) {
            Console.WriteLine("\nPsyCoLab\n1 - Launch PsyCoLab\n2 - Check / Repair PsyCoLab\n3 - Python Workspace\n4 - Exit");
            Console.Write("Choose 1-4: ");Console.Out.Flush();
            string choice=Answer();if(choice==null||choice.Trim()=="4")return 0;
            int result;
            try {
                if(choice.Trim()=="1")result=Launch(root,new string[0],splash:true);
                else if(choice.Trim()=="2")result=Check(root);
                else if(choice.Trim()=="3")result=Workspace(root);
                else {Console.WriteLine("Please choose 1, 2, 3 or 4.");continue;}
            }catch(Exception error){Console.WriteLine(error.Message);result=1;}
            if(result!=0)Console.WriteLine("The operation returned exit code "+result+". Choose 2 to check this installation. No experiment will be retried automatically.");
        }
    }
    public static int Launch(string root,string[] args,bool splash=false) {
        using(var lease=SourceRecovery.Acquire(root)) {
            var d=StartupRecovery.Diagnose(root);
            if(!d.healthy){Console.WriteLine(d.message+"\nChoose 2 - Check / Repair PsyCoLab. No installation was changed.");return 1;}
            return StartupRecovery.LaunchChecked(root,args,d,splash);
        }
    }
    public static int Check(string root) {
        StartupRecovery.Diagnosis d;
        using(var lease=SourceRecovery.Acquire(root))d=StartupRecovery.Diagnose(root);
        Console.WriteLine("\nInstallation check: "+d.category+"\n"+d.message);
        try{Console.WriteLine("Source setup Python: "+SourceRecovery.AvailablePython(root));}
        catch(Exception error){Console.WriteLine(error.Message);}
        bool repair=!d.healthy&&SourceRecovery.CanRepair(root),initial=SourceRecovery.CanInstall(root),restore=SourceRecovery.CanRestore(root);
        if(!repair&&!initial&&!restore) {
            if(!d.healthy)Console.WriteLine(StartupRecovery.Instructions(d)+"\n"+d.details);
            return d.healthy?0:1;
        }
        if(repair||initial)Console.WriteLine(SourceRecovery.Explanation+"\n"+(initial?"I - Install source environment":"R - Repair source installation"));
        if(restore)Console.WriteLine("S - Restore preserved environment (the old startup restriction may return; the replacement is retained separately)");
        Console.Write("B - Back without changes\nChoose an action: ");Console.Out.Flush();
        string action=(Answer()??"").Trim().ToUpperInvariant();
        if((repair&&action=="R")||(initial&&action=="I")||(restore&&action=="S")) {
            Console.Write("Proceed with this action? Type YES: ");Console.Out.Flush();
            if(!String.Equals(Answer(),"YES",StringComparison.OrdinalIgnoreCase)){Console.WriteLine("Cancelled. No repair action was performed.");return 0;}
            return SourceRecovery.Command(root,action=="S",false);
        }
        Console.WriteLine("No changes made.");return 0;
    }
    public static int Workspace(string root) {
        using(var lease=SourceRecovery.Acquire(root)) {
            var d=StartupRecovery.Diagnose(root);
            if(!d.healthy){Console.WriteLine(d.message+"\nChoose 2 - Check / Repair PsyCoLab first.");return 1;}
            string environment=Path.Combine(root,d.development?".venv-dev":".venv"),python=Path.Combine(environment,"Scripts","python.exe");
            Console.WriteLine("\nPython Workspace\nActive Python: "+python+"\n"+(d.development?"Source development environment; laboratory qualification is not granted.":"Existing qualified environment; changing packages may invalidate its checks.")+"\nRun python your_script.py, python -m pip list, or other commands. Type exit to return to the launcher.");
            var start=StartupRecovery.SourceProcess(root,new string[0],d.development);
            start.FileName=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"cmd.exe");start.Arguments="/d";start.CreateNoWindow=false;
            start.EnvironmentVariables["VIRTUAL_ENV"]=environment;
            start.EnvironmentVariables["PATH"]=Path.Combine(environment,"Scripts")+Path.PathSeparator+start.EnvironmentVariables["PATH"];
            start.EnvironmentVariables["PROMPT"]="(PsyCoLab) $P$G";
            start.EnvironmentVariables["PSYCOLAB_LAUNCH_ROLE"]=d.development?"development":"locked";
            using(var child=Process.Start(start)){child.WaitForExit();return child.ExitCode;}
        }
    }
}

// The source menu owns this short, best-effort console presentation.
public sealed class StartupSplash : IDisposable
{
    const string Escape = "\x1b[";
    const double PsyFadeSeconds = 10.0, GroupFadeSeconds = 0.7;
    const double FadeSeconds = PsyFadeSeconds+2*GroupFadeSeconds, SweepSeconds = 5.0, DockSeconds = 2.5;
    const int FrameMilliseconds = 33;
    // The logo's PSY, CO and LAB groups begin at columns 0, 25 and 42.
    const int CoStart = 25, LabStart = 42;
    const string Brand = "PsyCoLab", Cyan = Escape+"38;2;6;99;131m";
    const uint ProcessedInput = 0x1, QuickEdit = 0x40, ExtendedInput = 0x80;
    const uint ProcessedOutput = 0x1, WrapAtEndOfLine = 0x2, VirtualTerminalOutput = 0x4;
    static readonly string[] Logo = {
        "██████╗ ███████╗██╗   ██╗ ██████╗ ██████╗ ██╗      █████╗ ██████╗",
        "██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝██╔═══██╗██║     ██╔══██╗██╔══██╗",
        "██████╔╝███████╗ ╚████╔╝ ██║     ██║   ██║██║     ███████║██████╔╝",
        "██╔═══╝ ╚════██║  ╚██╔╝  ██║     ██║   ██║██║     ██╔══██║██╔══██╗",
        "██║     ███████║   ██║   ╚██████╗╚██████╔╝███████╗██║  ██║██████╔╝",
        "╚═╝     ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝"
    };
    static readonly int LogoWidth=Logo.Max(line=>line.Length);
    readonly IntPtr output;
    readonly uint outputMode;
    readonly bool cursorVisible;
    public bool Skipped {get; private set;}

    StartupSplash(IntPtr output,uint outputMode,bool cursorVisible) {
        this.output=output;this.outputMode=outputMode;this.cursorVisible=cursorVisible;
    }

    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int kind);
    [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr handle,out uint mode);
    [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr handle,uint mode);
    [DllImport("kernel32.dll",CharSet=CharSet.Unicode,ExactSpelling=true)]
    static extern bool WriteConsoleW(IntPtr handle,string value,uint count,out uint written,IntPtr reserved);

    static void Write(IntPtr output,string text) {
        uint written;
        if(!WriteConsoleW(output,text,(uint)text.Length,out written,IntPtr.Zero)||written!=text.Length)
            throw new IOException("Could not draw the startup splash.");
    }

    static string FadeFrame(int top,int left,double elapsed) {
        double groupPosition=elapsed<PsyFadeSeconds
            ?elapsed/PsyFadeSeconds
            :1+(elapsed-PsyFadeSeconds)/GroupFadeSeconds;
        var shades=new string[3];
        for(int group=0;group<shades.Length;group++) {
            double stage=Math.Max(0,Math.Min(1,groupPosition-group));
            double level=stage*stage*(3-2*stage);
            shades[group]=Escape+"38;2;"+(int)(6*level)+";"+(int)(99*level)+";"+(int)(131*level)+"m";
        }
        var colours=new string[LogoWidth];
        for(int col=0;col<LogoWidth;col++)
            colours[col]=shades[col<CoStart?0:col<LabStart?1:2];
        return Frame(top,left,colours);
    }

    static string SweepFrame(int top,int left,double progress) {
        double spread=LogoWidth*0.14;
        double centre=-3*spread+progress*(LogoWidth-1+6*spread);
        var colours=new string[LogoWidth];
        for(int col=0;col<LogoWidth;col++) {
            double distance=(col-centre)/spread;
            double glow=Math.Exp(-0.5*distance*distance);
            colours[col]=Escape+"38;2;"+(int)(6+39*glow)+";"+(int)(99+156*glow)+";"+(int)(131+124*glow)+"m";
        }
        return Frame(top,left,colours);
    }

    static string Frame(int top,int left,string[] colours) {
        var frame=new StringBuilder();
        for(int row=0;row<Logo.Length;row++) {
            frame.Append(Escape).Append(top+row).Append(';').Append(left).Append('H');
            string colour=null;
            for(int col=0;col<Logo[row].Length;col++) {
                char cell=Logo[row][col];
                if(cell!=' '&&colours[col]!=colour)frame.Append(colour=colours[col]);
                frame.Append(cell);
            }
        }
        return frame.ToString();
    }

    // Pack four samples of the existing block face into each terminal cell.
    static string[] ReducedLogo(int width,int height) {
        const string quadrants=" ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█";
        var rows=new string[height];
        for(int row=0;row<height;row++) {
            var line=new StringBuilder();
            for(int col=0;col<width;col++) {
                int bits=0;
                for(int sample=0;sample<4;sample++) {
                    int x=(2*col+sample%2)*LogoWidth/(2*width);
                    int y=(2*row+sample/2)*(Logo.Length-1)/(2*height);
                    if(x<Logo[y].Length&&Logo[y][x]=='█')bits|=1<<sample;
                }
                line.Append(quadrants[bits]);
            }
            rows[row]=line.ToString();
        }
        return rows;
    }

    static bool Interrupted(int columns,int rows) {
        if(Console.KeyAvailable){Console.ReadKey(true);return true;}
        return Console.WindowWidth!=columns||Console.WindowHeight!=rows;
    }

    bool Animate(int columns,int rows) {
        int top=(rows-Logo.Length)/2+1,left=(columns-LogoWidth)/2+1;
        var timer=Stopwatch.StartNew();
        while(timer.Elapsed.TotalSeconds<FadeSeconds) {
            if(Interrupted(columns,rows))return false;
            Write(output,FadeFrame(top,left,timer.Elapsed.TotalSeconds));
            System.Threading.Thread.Sleep(FrameMilliseconds);
        }
        timer.Restart();
        while(timer.Elapsed.TotalSeconds<SweepSeconds) {
            if(Interrupted(columns,rows))return false;
            Write(output,SweepFrame(top,left,timer.Elapsed.TotalSeconds/SweepSeconds));
            System.Threading.Thread.Sleep(FrameMilliseconds);
        }
        string[][] sizes={Logo,ReducedLogo(49,5),ReducedLogo(33,3),ReducedLogo(23,2),new[]{Brand}};
        int previousTop=top,previousLeft=left,previousHeight=Logo.Length,previousWidth=LogoWidth;
        timer.Restart();
        while(true) {
            if(Interrupted(columns,rows))return false;
            double progress=Math.Min(1,timer.Elapsed.TotalSeconds/DockSeconds);
            var logo=sizes[Math.Min(sizes.Length-1,(int)(progress*sizes.Length))];
            double ease=progress*progress*(3-2*progress);
            int y=(int)Math.Round(top+(1-top)*ease),x=(int)Math.Round(left+(2-left)*ease);
            var frame=new StringBuilder(Cyan);
            for(int row=0;row<previousHeight;row++)
                frame.Append(Escape).Append(previousTop+row).Append(';').Append(previousLeft).Append('H')
                     .Append(Escape).Append(previousWidth).Append('X');
            for(int row=0;row<logo.Length;row++)
                frame.Append(Escape).Append(y+row).Append(';').Append(x).Append('H').Append(logo[row]);
            Write(output,frame.ToString());
            if(progress==1)return true;
            previousTop=y;previousLeft=x;previousHeight=logo.Length;previousWidth=logo.Max(line=>line.Length);
            System.Threading.Thread.Sleep(FrameMilliseconds);
        }
    }

    public static StartupSplash Begin() {
        StartupSplash splash=null;
        try {
            if(Environment.GetEnvironmentVariable("PSYCOLAB_SKIP_INTRO")=="1")return null;
            var output=GetStdHandle(-11);
            var input=GetStdHandle(-10);
            uint outputMode,inputMode;
            // Redirected launches must leave scripted input and output alone.
            if(!GetConsoleMode(output,out outputMode)||!GetConsoleMode(input,out inputMode))return null;
            int columns=Console.WindowWidth,rows=Console.WindowHeight;
            bool cursorVisible=Console.CursorVisible;
            if(columns<=LogoWidth||rows<=Logo.Length||
                !SetConsoleMode(output,(outputMode|ProcessedOutput|VirtualTerminalOutput)&~WrapAtEndOfLine)) {
                if(columns>Brand.Length)Write(output,Brand+"\r\n");
                return null;
            }
            splash=new StartupSplash(output,outputMode,cursorVisible);
            // Prevent selection from pausing the splash and treat Ctrl+C as a skip key.
            bool inputChanged=SetConsoleMode(input,(inputMode|ExtendedInput)&~(ProcessedInput|QuickEdit));
            try {
                Write(output,Escape+"?1049h"+Escape+"?25l"+Escape+"48;2;0;0;0m"+Escape+"2J");
                splash.Skipped=!inputChanged||!splash.Animate(columns,rows);
                if(splash.Skipped)Write(output,Escape+"2J");
                Write(output,Escape+"0m");
                // The child inherits normal input/output modes. The alternate
                // screen alone stays active until Textual takes it over.
                SetConsoleMode(output,outputMode);
                return splash;
            }finally {
                if(inputChanged)SetConsoleMode(input,inputMode);
            }
        }catch(Exception) {
            if(splash!=null)splash.Dispose();
            return null; // Launch normally when the console cannot draw the intro.
        }
    }

    public void Dispose() {
        try {
            if(SetConsoleMode(output,outputMode|ProcessedOutput|VirtualTerminalOutput))
                Write(output,Escape+"?1049l"+Escape+(cursorVisible?"?25h":"?25l"));
        }catch(Exception) { /* A closed terminal cannot be restored. */ }
        finally {SetConsoleMode(output,outputMode);}
    }
}

public class RecoveryWindow : Form
{
    public int Result=1;
    public RecoveryWindow(StartupRecovery.Diagnosis d,List<StartupRecovery.Candidate> retained,string package) {
        Result=d.healthy?0:1;
        Text="PsyCoLab startup recovery";Width=800;Height=480;StartPosition=FormStartPosition.CenterScreen;
        bool available=!d.healthy&&!d.after_application&&StartupRecovery.PackageAvailable(package);
        string recommended=StartupRecovery.Recommendation(d,retained.Count,available);
        var layout=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(16),AutoScroll=true};Controls.Add(layout);
        layout.Controls.Add(new Label{Text=d.message,AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
        layout.Controls.Add(new Label{Text="Recommended because: "+StartupRecovery.Reason(recommended),AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
        if(!d.healthy&&!d.after_application&&SourceRecovery.CanRepair(d.root)) {
            layout.Controls.Add(new Label{Text=SourceRecovery.Explanation,AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
            var repair=new Button{AutoSize=true,Text="Repair older source installation"+(recommended=="repair"?" [Recommended]":"")};layout.Controls.Add(repair);
            repair.Click+=async(s,e)=>{
                if(MessageBox.Show(this,SourceRecovery.Explanation+"\n\nContinue?",Text,MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
                Enabled=false;Hide();try{Result=await Task.Run(()=>SourceRecovery.Execute(d.root,false));Close();}
                catch(Exception error){Show();Enabled=true;MessageBox.Show(this,error.Message+"\nRun recovery again to retry. The preserved environment is retained.",Text);}
            };
        }
        if(d.healthy) {
            var open=new Button{AutoSize=true,Text="Open PsyCoLab"};layout.Controls.Add(open);
            open.Click+=(s,e)=>{Hide();try{Result=StartupRecovery.LaunchSource(d.root,new string[0]);}finally{Close();}};
        }
        if(!d.after_application&&SourceRecovery.CanRestore(d.root)) {
            var restore=new Button{AutoSize=true,Text="Restore preserved environment"};layout.Controls.Add(restore);
            restore.Click+=async(s,e)=>{
                if(MessageBox.Show(this,"Restore the original environment to its original location? The replacement will be preserved separately. The old startup error may return; restoration does not approve qualification.",Text,MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
                Enabled=false;try{Result=await Task.Run(()=>SourceRecovery.Execute(d.root,true));MessageBox.Show(this,"Original environment restored. No application was launched.",Text);Close();}
                catch(Exception error){Enabled=true;MessageBox.Show(this,error.Message,Text);}
            };
        }
        if(!d.healthy&&!d.after_application&&StartupRecovery.DeveloperCheckout(d.root)&&!Directory.Exists(Path.Combine(d.root,".venv"))) {
            layout.Controls.Add(new Label{Text="Maintaining this Git checkout? Open PsyCoLab.bat, choose 2 - Check / Repair PsyCoLab, then 1 - Launch PsyCoLab. It uses installed 64-bit Python 3.11 in a separate development environment; laboratory qualification is not granted.",AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
        }
        if(retained.Count==0)layout.Controls.Add(new Label{Text="No verified retained installation is available for this recovery.",AutoSize=true});
        if(!available)layout.Controls.Add(new Label{Text="No separate-install action is verified and available for this recovery.",AutoSize=true});
        if(retained.Count>0) {
            var choices=new ComboBox{Width=720,DropDownStyle=ComboBoxStyle.DropDownList};foreach(var c in retained)choices.Items.Add(c);choices.SelectedIndex=0;layout.Controls.Add(choices);
            var launch=new Button{AutoSize=true,Text="Open verified retained installation"+(recommended=="retained"?" [Recommended]":"")};layout.Controls.Add(launch);
            launch.Click+=(s,e)=>{var selected=(StartupRecovery.Candidate)choices.SelectedItem;Hide();try{if(selected.instance!=null)StartupRecovery.LaunchFixed(selected.instance);else StartupRecovery.LaunchSource(selected.root,new string[0]);}finally{Close();}};
        }
        if(available) {
            var separate=new Button{AutoSize=true,Text="Create separate approved installation"+(recommended=="separate"?" [Recommended]":"")};layout.Controls.Add(separate);
            separate.Click+=(s,e)=>{try{SetupEngine.CheckPackage(package,()=>false);using(var setup=new SetupWindow(package,StartupRecovery.Store))setup.ShowDialog(this);}catch(Exception error){MessageBox.Show(this,"Package validation failed. No installation was approved.\n"+error.Message,Text);}};
        }
        var diagnostics=new Button{AutoSize=true,Text="View diagnostics and administrator instructions"+(recommended=="diagnostics"?" [Recommended]":"")};layout.Controls.Add(diagnostics);
        diagnostics.Click+=(s,e)=>{try{string path=Path.Combine(Path.GetTempPath(),"psycolab-startup-"+Guid.NewGuid().ToString("N")+".json");SetupEngine.Save(path,new{diagnosis=d,recommendation=recommended,reason=StartupRecovery.Reason(recommended),verified_retained_count=retained.Count,verified_package=available,instructions=StartupRecovery.Instructions(d)});Process.Start("notepad.exe",SetupEngine.Quote(path));}catch(Exception error){MessageBox.Show(this,"Could not open diagnostics.\n"+error.Message,Text);}};
        var cancel=new Button{AutoSize=true,Text="Cancel"+(recommended=="cancel"?" [Recommended]":"")};layout.Controls.Add(cancel);cancel.Click+=(s,e)=>Close();CancelButton=cancel;
        layout.Controls.Add(new Label{Text="Cancel performs no recovery action. Source, qualification evidence, calibration and experimental records are preserved.",AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
    }
}
