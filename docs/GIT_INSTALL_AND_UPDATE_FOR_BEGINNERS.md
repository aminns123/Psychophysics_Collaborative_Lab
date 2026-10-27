# Installing and Updating PsyCoLab with Git — Beginner's Guide (Windows)

This page is for students and researchers who want to install PsyCoLab for the first time, or keep an existing installation updated. **You can use your own GitHub account. You do not need the project maintainer's account.** The official public repository is:

https://github.com/aminns123/Psychophysics_Collaborative_Lab

**The short rule:** use **git clone** once to make your first project folder, and then use **git pull** inside that folder to receive later approved updates. **Do not extract a new GitHub ZIP over an existing project.**

## 1. Before you begin

On a Windows computer:

1. Install [Git for Windows](https://git-scm.com/downloads/win) if necessary.
2. Install **64-bit Python 3.11**. PsyCoLab currently requires Python 3.11; do not substitute a newer interpreter.
3. Open **Windows PowerShell** (or Windows Terminal with a PowerShell tab). You do not need to launch GitHub Desktop or sign in to the maintainer's account.
4. Confirm that Git is available:

~~~powershell
git --version
~~~

If PowerShell says that Git is not recognised, install Git for Windows and then **close and reopen** PowerShell.

The instructions below use the Documents folder as an example. You may choose a different writable parent folder; the folder does **not** need to be called Documents. If Windows stores Documents in OneDrive, navigate to your preferred location instead.

## 2. First-time installation: clone the repository

Navigate to the parent folder where you want your new PsyCoLab folder:

~~~powershell
cd "$HOME\Documents"
~~~

Download a Git-managed copy of the official project:

~~~powershell
git clone https://github.com/aminns123/Psychophysics_Collaborative_Lab.git
~~~

Git creates a new folder named **Psychophysics_Collaborative_Lab**. Enter it:

~~~powershell
cd .\Psychophysics_Collaborative_Lab
~~~

You now have a Git checkout connected to the official repository. This command is only needed **once per fresh installation**. Do not use it every time you want an update.

To launch PsyCoLab, double-click **run_psycolab.bat** in File Explorer (or run the launcher from this project folder). The launcher prepares the machine-local virtual environment; internet/package-index access is needed during initial setup. Follow the on-screen setup instructions for the external data location and your own display.

**Important:** downloading code does not calibrate a laboratory monitor or qualify the computer for human measurements. The actual hardware and experiment must still be checked.

See the [full installation guide](INSTALLATION.md) for Python, dependencies, monitor setup, and more detailed checks.

## 3. Future updates: pull the latest approved main branch

Open PowerShell and navigate **inside the existing cloned project**, for example:

~~~powershell
cd "$HOME\Documents\Psychophysics_Collaborative_Lab"
~~~

Check whether you have local changes:

~~~powershell
git status
~~~

If Git says the working tree is clean and you are using the official repository directly, update safely:

~~~powershell
git fetch origin
git switch main
git pull --ff-only origin main
~~~

The **--ff-only** option makes Git refuse an unexpected merge instead of silently creating one. If an error occurs, **stop and inspect it** rather than forcing the update.

Then launch **run_psycolab.bat** again so PsyCoLab can check its local Python environment. Inspect your selected experiment, saved values, display profile and any laboratory extensions before collecting data.

**Remember:** cloning is the first-time step; pulling is the repeat-update step.

## 4. Does it matter which GitHub account I use?

Usually, **no**. The official PsyCoLab repository is public, so students can clone and fetch it without access to the maintainer's GitHub login. A student's own GitHub account is useful when they want to maintain their own fork, contribute changes, or open a pull request.

See which repository the local folder follows:

~~~powershell
git remote -v
~~~

If **origin** points to **aminns123/Psychophysics_Collaborative_Lab.git**, the update instructions in Section 3 apply.

If **origin** instead points to the student's **own fork**, connect the official repository once as **upstream**:

~~~powershell
git remote add upstream https://github.com/aminns123/Psychophysics_Collaborative_Lab.git
~~~

Check the remotes again, and then fetch the official changes:

~~~powershell
git fetch upstream
~~~

To update an unchanged local main branch from the official main branch:

~~~powershell
git switch main
git merge --ff-only upstream/main
~~~

If this refuses because the student's branch has diverged, do not force a reset; preserve the student's commits and seek help resolving the branch history. Updating the student's fork on GitHub is a separate step and does not occur automatically.

## 5. What happens to my own experiments, settings and data?

PsyCoLab is intentionally arranged so researchers can update **shared framework code** without automatically replacing their **own scientific work**:

| Type of work | Where it belongs | Update implication |
| --- | --- | --- |
| Official PsyCoLab files | Git checkout | These are the files Git updates; changes made directly to them may conflict. |
| Custom lab experiments and stimuli | Trusted **external PsyCoLab_Extensions folder** | Separate from the checkout, so an ordinary framework pull does not replace their files. |
| Named run presets and local preferences | External local configuration folder | Keep and back up separately. |
| Monitor calibration and measurements | External local configuration folder | Keep and back up separately; recheck the actual apparatus when required. |
| Participant and synthetic run data | External data folder | Not part of Git updates; back up independently. |

On its first normal launch, PsyCoLab can prepare a starter **PsyCoLab_Extensions** folder alongside the checkout. It must be explicitly reviewed and trusted in **Build Experiments → Laboratory Extensions**. Extensions are **not automatically enabled or marked Ready**. After changes to scientific dependencies, they may need to be tested and marked Ready again.

See [laboratory extensions](LABORATORY_EXTENSIONS.md) and [safe updates and local research](SAFE_UPDATES_AND_LOCAL_WORK.md).

**Do not** keep your only copy of experimental recordings, private student work or calibration measurements inside the framework checkout. Do not assume that an ignored file is protected if the whole directory is deleted.

## 6. I previously downloaded a ZIP. How do I switch to Git?

A downloaded GitHub ZIP is a snapshot, **not** a Git checkout. Typing **git pull** in the extracted ZIP folder will generally show **not a git repository**.

The safe approach is:

1. **Back up the old folder** and separately back up any local configuration, calibrations, extensions and participant data.
2. Follow Section 2 to **clone into a new folder**. Do not clone over the ZIP contents.
3. Inspect the old folder and migrate only your own research work into PsyCoLab's supported **external** extension, configuration and data locations. Do not blindly copy old core Python files or environments into the new checkout.
4. Launch the new installation, choose your existing external data/configuration locations as appropriate, verify your monitor and experiment, and confirm that the intended lab source still works.
5. Keep the backed-up old version until the new installation has passed your checks.

Never unzip a new source archive on top of a working PsyCoLab folder.

## 7. If Git reports an error

| Message or situation | What to do |
| --- | --- |
| **git is not recognised** | Install Git for Windows and restart PowerShell. |
| **not a git repository** | You are not inside a cloned checkout, or your folder came from a ZIP. Follow Section 6 if necessary. |
| **local changes would be overwritten** | Stop. Review **git status**; commit tracked research changes on a separate branch or make a verified backup before updating. |
| **--ff-only refuses the update** | Your local branch has commits or has diverged. Do not force or reset; inspect the history and ask for help. |
| **origin points to my fork** | Use the **upstream** instructions in Section 4. |
| **PsyCoLab fails to launch after updating** | Retain the error message and current commit; rerun the launcher and consult the full installation and safe-update guides. Do not delete acquired data or calibration. |

**Never use destructive Git commands such as git reset --hard or git clean -fdx as a quick fix.** The latter can delete even ignored local files. Do not use a ZIP overlay, and do not copy another computer's virtual environment or calibration as a substitute for setting up your own machine.

## 8. Quick reference

**First installation (once):**

~~~powershell
cd "$HOME\Documents"
git clone https://github.com/aminns123/Psychophysics_Collaborative_Lab.git
cd .\Psychophysics_Collaborative_Lab
~~~

Then double-click **run_psycolab.bat**.

**Routine update (later, from an unchanged direct clone):**

~~~powershell
cd "$HOME\Documents\Psychophysics_Collaborative_Lab"
git status
git fetch origin
git switch main
git pull --ff-only origin main
~~~

Then launch **run_psycolab.bat**, review your scientific settings, and recheck readiness/calibration as appropriate.

For contributions to the shared project, use a separate branch or fork and a reviewed pull request. Read the [contributor guide](CONTRIBUTING_EXPERIMENTS.md). For safer, more detailed recovery procedures, read the [safe-update guide](SAFE_UPDATES_AND_LOCAL_WORK.md).
