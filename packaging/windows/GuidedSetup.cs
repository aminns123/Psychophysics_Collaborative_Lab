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
            if(args.Length==2&&args[0]=="--launch")return StartupRecovery.LaunchFixed(SetupEngine.Full(args[1]));
            if(args.Length>=2&&args[0]=="--source")return StartupRecovery.LaunchSource(SetupEngine.Full(args[1]),args.Skip(2).ToArray());
            if(args.Length==2&&args[0]=="--recover")return StartupRecovery.Recover(SetupEngine.Full(args[1]));
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
    public class Diagnosis {
        public string category,message,details,root,original_root;
        public bool healthy,after_application;
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
    public static Diagnosis Inspect(string root) {
        try {
            root=SetupEngine.Full(root);SetupEngine.Plain(root);
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
    public static ProcessStartInfo SourceProcess(string root,IEnumerable<string> args) {
        var start=SetupEngine.Start(Path.Combine(root,".venv","Scripts","python.exe"),args,root);
        // Existing explicit laboratory roots remain authoritative for a source checkout.
        foreach(string key in new[]{"PSYCOLAB_CONFIG_DIR","PSYCOLAB_DATA_DIR"}) {
            string value=Environment.GetEnvironmentVariable(key);if(!String.IsNullOrWhiteSpace(value))start.EnvironmentVariables[key]=value;
        }
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
            var start=SourceProcess(root,new[]{"-I","-B",Path.Combine(root,"scripts","launcher_setup.py"),"--check"});
            start.RedirectStandardOutput=true;start.RedirectStandardError=true;
            using(var p=Process.Start(start)) {
                var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();p.WaitForExit();
                d.details=output.Result+error.Result;
                if(p.ExitCode!=0)return Problem(root,"qualification_check_failed","The existing read-only qualification check failed. This may concern installed files, interpreter or editable-source identity; see the diagnostic evidence.",d.details);
            }
            d.healthy=true;d.category="healthy";d.message="This checkout passed its existing read-only qualification checks. No installation, repair or requalification was performed.";
        }catch(Exception error){return Problem(root,"environment_or_source_damaged","This installation could not pass its existing source/environment checks. Nothing was repaired.",error.Message);}
        return d;
    }
    public static List<Candidate> Retained(Diagnosis failure,string store) {
        var result=new List<Candidate>();if(failure.healthy||failure.after_application)return result;
        if(!String.IsNullOrWhiteSpace(failure.original_root)&&Directory.Exists(failure.original_root)) {
            var original=Diagnose(failure.original_root);if(original.healthy)result.Add(new Candidate{root=original.root,label="Verified original checkout: "+original.root});
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
        if(!d.after_application&&retained>0)return "retained";
        if(!d.after_application&&package)return "separate";
        return "diagnostics";
    }
    public static string Reason(string option) {
        if(option=="cancel")return "The installation already passes its checks. Close recovery and use run_psycolab.bat for ordinary launch.";
        if(option=="retained")return "A retained installation has already passed its existing read-only checks. Using it preserves the failing checkout and all its evidence.";
        if(option=="separate")return "This host's sealed package and every required artifact verified. The existing guided setup can create a separate installation without replacing this one.";
        return "No automatic correction has been established for this failure. Diagnostics give the administrator the verified evidence without changing this installation.";
    }
    public static string Instructions(Diagnosis d) {
        string common="Preserve the source, environment, qualification records, calibration and data. Never edit a qualification record, install dependencies in place or repeat acquisition automatically. ";
        if(d.after_application)return common+"Inspect the application's existing crash/fatal and incomplete-run records. The exit phase is diagnostic evidence, not authority to resume or repeat an experiment.";
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
    static int Observe(ProcessStartInfo start,string root) {
        string phase=null,applicationReport=null;
        // One exit notification over a private OS pipe; no marker in source or data.
        string name="PsyCoLabStartup-"+Guid.NewGuid().ToString("N");
        using(var pipe=new System.IO.Pipes.NamedPipeServerStream(name,System.IO.Pipes.PipeDirection.In,1,System.IO.Pipes.PipeTransmissionMode.Byte,System.IO.Pipes.PipeOptions.Asynchronous)) {
            var read=Task.Run(()=>{try{pipe.WaitForConnection();using(var reader=new StreamReader(pipe,Encoding.UTF8)){var notice=SetupEngine.Json.Deserialize<ExitNotice>(reader.ReadLine());phase=notice.phase;applicationReport=notice.report;}}catch(Exception){ /* Missing or malformed evidence remains unknown. */ }});
            start.EnvironmentVariables["PSYCOLAB_STARTUP_PIPE"]=name;start.CreateNoWindow=false;
            int code;bool started=false;
            try{using(var child=Process.Start(start)){started=true;child.WaitForExit();code=child.ExitCode;}}
            catch(Exception error){var failed=Problem(root,"application_start_failed",started?"Application completion could not be observed. An experiment may still be running; do not retry it.":"Windows could not start the verified application. See diagnostics.",error.Message);failed.after_application=started;Show(failed);return 1;}
            if(code==0||code==75||code==130)return code;
            // A late/missing notification is conservatively an unknown incident.
            read.Wait(250);var incident=Incident(root,code,phase);incident.details+="; application crash report: "+(applicationReport??"not reported");Show(incident);return code;
        }
    }
    public class ExitNotice { public string phase,report; }
    public static int LaunchSource(string root,string[] args) {
        var d=Diagnose(root);if(!d.healthy){Show(d);return 1;}
        return Observe(SourceProcess(root,SetupEngine.ApplicationArguments(args)),root);
    }
    public static int LaunchFixed(string instance) {
        try {
            var record=SetupEngine.Load(instance);string root=Path.Combine(instance,"source");
            // Full packaged-source enumeration remains authoritative, including added files.
            SetupEngine.Validate(instance,record,Path.Combine(Path.GetTempPath(),"psycolab-fixed-check-"+Guid.NewGuid().ToString("N")+".log"),()=>false);
            var start=SourceProcess(root,SetupEngine.ApplicationArguments(new string[0]));
            start.EnvironmentVariables["PSYCOLAB_CONFIG_DIR"]=String.IsNullOrWhiteSpace(record.config_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","LaboratoryConfiguration"):record.config_root;
            start.EnvironmentVariables["PSYCOLAB_DATA_DIR"]=String.IsNullOrWhiteSpace(record.data_root)?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"PsyCoLabData"):record.data_root;
            return Observe(start,root);
        }catch(Exception error){Show(Problem(instance,"fixed_installation_failed","This fixed-version installation failed validation. Its identity and files were preserved.",error.Message));return 1;}
    }
    public static int Recover(string root) {var d=Diagnose(root);Show(d);return d.healthy?0:1;}
    public static void Show(Diagnosis d) {
        using(var window=new RecoveryWindow(d,Retained(d,Store),AppDomain.CurrentDomain.BaseDirectory))window.ShowDialog();
    }
}

public class RecoveryWindow : Form
{
    public RecoveryWindow(StartupRecovery.Diagnosis d,List<StartupRecovery.Candidate> retained,string package) {
        Text="PsyCoLab startup recovery";Width=800;Height=480;StartPosition=FormStartPosition.CenterScreen;
        bool available=!d.healthy&&!d.after_application&&StartupRecovery.PackageAvailable(package);
        string recommended=StartupRecovery.Recommendation(d,retained.Count,available);
        var layout=new FlowLayoutPanel{Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(16),AutoScroll=true};Controls.Add(layout);
        layout.Controls.Add(new Label{Text=d.message,AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
        layout.Controls.Add(new Label{Text="Recommended because: "+StartupRecovery.Reason(recommended),AutoSize=true,MaximumSize=new System.Drawing.Size(730,0)});
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
