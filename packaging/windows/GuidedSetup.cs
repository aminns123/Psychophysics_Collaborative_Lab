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
        var pack=ReadBundle(bundle);
        if(pack.schema_version!=1||pack.files==null||pack.source_files==null||pack.interpreter_files==null)throw new IOException("Unsupported installation package.");
        progress("Checking the complete package. No existing installation will be replaced.");
        Verify(bundle,pack.files,cancelled);
        if(pack.source_files.Count==0||pack.interpreter_files.Length==0||pack.source_files.Any(entry=>!pack.files.ContainsKey("source/"+entry.Key)||pack.files["source/"+entry.Key]!=entry.Value)||pack.interpreter_files.Any(path=>!pack.files.ContainsKey(path))||!pack.files.ContainsKey("wheels/"+pack.wheel_probe))throw new IOException("The package inventory is inconsistent. Obtain a complete reviewed package.");
        if(pack.files["tools/conda.exe"]!="147e07937bb6509b69e9630eec6c6a281cd916c246d5fa5851a8b8f3b502f31f")throw new IOException("Unrecognised provisioning tool; obtain a reviewed setup package.");
        Directory.CreateDirectory(store);
        using(var guard=new FileStream(Path.Combine(store,"setup.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)) {
            Save(Path.Combine(store,".psycolab-installations.json"),new{schema_version=1});
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
    }
    public static Installation Load(string instance) {
        Plain(instance);var r=Read<Installation>(Path.Combine(instance,"installation.json"));
        if(r.schema_version!=1||r.id!=Path.GetFileName(Full(instance))||r.id.Length!=32||r.source_files==null||r.source_files.Count==0)throw new IOException("Installation identity is missing or changed. Use its original shortcut or install separately.");return r;
    }
    public static void Validate(string instance,Installation record,string log,Func<bool> cancelled) {
        LastLog=log;
        string source=Path.Combine(instance,"source");Verify(source,record.source_files,cancelled);
        // A new untracked experiment/module must not slip past the source seal.
        var pending=new Stack<string>();pending.Push(source);
        while(pending.Count>0)foreach(string path in Directory.EnumerateFileSystemEntries(pending.Pop())) {
            Plain(path);string relative=path.Substring(source.Length+1).Replace('\\','/');
            if(Directory.Exists(path)) {
                if(relative==".venv"||relative==".psycolab_logs"||relative.EndsWith(".egg-info")||relative.EndsWith("__pycache__"))continue;
                pending.Push(path);
            }else if(!record.source_files.ContainsKey(relative))throw new IOException("This installation has added or changed source files. Install a reviewed version separately; it was preserved.");
        }
        Run(Start(Path.Combine(source,".venv","Scripts","python.exe"),new[]{"-I","-B",Path.Combine(source,"scripts","launcher_setup.py"),"--check"},source),log,cancelled);
    }
    public static void Launch(string instance,Func<bool> cancelled=null) {
        cancelled=cancelled??(()=>false);
        var record=Load(instance);Validate(instance,record,Path.Combine(Path.GetTempPath(),"psycolab-launch-"+Guid.NewGuid().ToString("N")+".log"),cancelled);
        if(cancelled())throw new OperationCanceledException();
        string source=Path.Combine(instance,"source");var start=Start(Path.Combine(source,".venv","Scripts","python.exe"),new[]{"-I","-B","-m","psychophysics_lab"},source);start.CreateNoWindow=false;
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
            if(args.Length==2&&args[0]=="--launch"){SetupEngine.Launch(SetupEngine.Full(args[1]));return 0;}
            string bundle=AppDomain.CurrentDomain.BaseDirectory,store=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PsyCoLab","Installations");
            if(args.Length==4&&args[0]=="--bundle"&&args[2]=="--store"){bundle=SetupEngine.Full(args[1]);store=SetupEngine.Full(args[3]);}
            else if(args.Length!=0)throw new ArgumentException("Open PsyCoLab Setup or use a version-specific shortcut.");
            Application.Run(new SetupWindow(bundle,store));return 0;
        }catch(Exception ex){MessageBox.Show(ex.Message+"\nOpen PsyCoLab Setup to install separately or select another retained version. No automatic repair was attempted.","PsyCoLab — recovery",MessageBoxButtons.OK,MessageBoxIcon.Information);return 1;}
    }
}
