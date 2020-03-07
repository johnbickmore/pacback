
# Pacback - Beta 2.0
**TLDR: This project's goal is to provide orchestrated version control for Arch Linux while maintaining a small footprint and fast performance.**

### Index:
1. [CLI Commands](https://github.com/JustinTimperio/pacback#pacback-cli-commands-and-flags)
2. [Install Instructions](https://github.com/JustinTimperio/pacback#install-instructions)
3. [Usage Examples](https://github.com/JustinTimperio/pacback#pacback-usage-examples)
4. [Pacback's Design](https://github.com/JustinTimperio/pacback#pacbacks-design)
5. [Feature Path and Bugs](https://github.com/JustinTimperio/pacback#feature-path-known-bugs-issues-and-limitations)
 
## Abstract:
I love Arch Linux and rolling-release distros. Being at the head of Linux kernel and application development means access to the latest features and bug fixes. This also often means dealing with the latest bugs. While I don't run into major bugs often, when they happen, they cripple my productivity. Reversing individual packages is generally a slow manual process and while some tools exist, none meet my needs. In particular, support for downgrading AUR packages is extremely lacking.  

## Core Features:

- Resilient Downgrades and Upgrades
- Rolling System SnapShots
- Rollback to Arch Archive Dates
- Ability to Track All Additions, Removals, and Upgrades Made to the System
- Native AUR Support
- Automatically Save and Restore App Config Files
- FailProof Rollbacks Even When Caches Are Deleted
- Multi-Threaded Operations


-------------------


## Pacback CLI Commands and Flags:
Pacback offers a few core commands that streamline the process of creating and restoring versions. The CLI is designed to be dead simple and provide detailed feedback and user control.

### Core Commands
* -c, --create_rp | Generate a pacback restore point. Takes a restore point # as an argument.\
**Example: `pacback -c 1`**
* -rb, --rollback | Rollback to a previously generated restore point or to an archive date.\
**Example: `pacback -rb 1` or `pacback -rb 2019/08/14`**
* -ss, --snapshot | Restore the system to an automaticly created snapshot.\
**Example: `pacback -ss 2`**
* -pkg, --rollback_pkgs | - Rollback a list of packages looking for old versions on the system.\
**Example: `pacback -pkg zsh cpupower neovim`**

### Flags
* -f, --full_rp | Generate a pacback full restore point.\
**Example: `pacback -f -c 1`**
* -d, --add_dir | Add any custom directories to your restore point during a `--create_rp AND --full_rp`.\
**Example: `pacback -f -c 1 -d /dir1/to/add /dir2/to/add /dir3/to/add`**
* -nc, --no_confirm | Skip asking user questions during RP creation. Will answer yes to all.\
**Example: `pacback -nc -c 1`**
* -n, --notes | Add Custom Notes to Your Metadata File.\
**Example: `pacback -nc -c 1 -f -n 'Here Are Some Notes'`**

### Info Show
* -i, --info | Print information about a retore point.\
* **Example: `pacback -i 1`**
* -ls, --list | List information about all Restore Points and Snapshots.\
**Example: `pacback -ls`**
* -v, --version | Display Pacback version.\
**Example: `pacback -v`**

### Utilities
* -rm, --remove | Removes the selected Restore Point.\
**Example: `pacback -rm 12 -nc`**
* --install_hook | Install a pacman hook that creates a snapshot during each pacman upgrade.\
**Example: `pacback --install_hook`**
* --remove_hook | Removes the pacman hook that creates snapshots.\
**Example: `pacback --remove_hook`**
* --clean | Clean old and orphaned pacakages along with old Restore Points. Provide the number of package you want keep.\
**Example: `pacback --clean 3`**


------------------


## Install Instructions:
Pacback offers two AUR packages. (Special thanks to [Attila Greguss](https://github.com/Gr3q) for maintaining them.)

*Don't forget to run **`sudo pacback --install_hook`** after installing!*

[pacback](https://aur.archlinux.org/packages/pacback): This is the recommended install for most users. Releases mark stable points in Pacbacks development, preventing unnecessary upgrades/changes that may introduce instability into production machines. 

[pacback-git](https://aur.archlinux.org/packages/pacback-git): This package fetches the latest version from git. The master branch will be unstable periodically but is ideal for anyone looking to contribute to pacbacks development or if you want access to the latest features and patches.

### Upgrading From Git to AUR:
If you are upgrading from a cloned git repo please follow these steps.
1. `cd /path/to/repo`
2. `git pull && git submodule update --recursive --init` (Upgrade before migration)
3. `sudo pacback -ls` (This also initiates a check that confirms everything is configured)
4. `sudo rm /usr/bin/pacback` (Remove the old symlink)
5. `pacaur -S pacback` (Install pacback with an AUR Manager)
6. `sudo rm -R /path/to/repo` (Remome now unused git repo)


------------------


## Pacback Usage Examples:
While there are only a few CLI commands, they can be used in a wide variety of complex restoration tasks. Below are some examples of how to use and deploy Pacback in your systems. 

### Rolling System Snapshots
One of the problems with rolling releases is you never know when a problem might occur. It may be months before you run into an issue, at which point, you will need to scramble to figure out when your system was stable last. By using the integrated pacman hook, Pacback creates a restore point every time you make any change to the system. This means at any point you can revert your system to any point in time without creating a restore point ahead of time. This also gives a high degree of granularity when making many small changes throughout the day.

1. Install the Pacback hook  with: `pacback --install_hook`
2. Make a series of changes to your system: `pacman -S tree && pacman -S rsync`
3. Run `pacback -ls` and you should see `SS #00` and `SS #01`. Each time you make a change (add, remove, upgrade package) a snapshot will be created during the transaction.
4. Remove the rsync pacakge by restoring snapshot #00 OR remove both rsync and tree by restoring snapshot #01.

![Pacback Snapback]()

### Rollback a List of Packages 
Most issues introduced by an upgrade stem from a single package or a set of related packages. Pacback allows you to selectively rollback a list of packages using `pacback -pkg`. Packback searches your file system looking for all versions associated with each package name. When searching, Pacback attempts to avoid matching generic names used by multiple packages (I.E. *xorg* in *xorg*-server, *xorg*-docs, *xorg*-xauth). If no packages are found, the search parameters can be widened but it will likely show inaccurate results.

In this example, we selectively rollback 2 packages.
1. `pacback -pkg typescript electron`

![Pacback Rolling Back a List of Packages](https://imgur.com/Rhy6iDn.gif)

### Rolling Back to an Archive Date
Another popular way to rollback is to fetch packages directly from the Arch Linux Archives using pacman. Pacback automates this entire process with the `pacback -rb` command. To rollback to a specific date, give `-rb` a date in YYYY/MM/DD format and Pacback will automatically save your mirrorlist, point a new mirrorlist to an archive URL, then run a full system downgrade. 

1. `pacback -rb 2019/10/18`

![Pacback Rolling Back an Archive Date](https://imgur.com/nBaYYCB.gif)


### Backup Version Sensitive Application Data
In some cases, config files may need to be modified when updating packages. In other cases, you may want to backup application data before deploying an upgrade in case of error or corruption. Pacback makes it extremely simple to store these files and will automatically compare files you have stored against your current file system. Once checksumming is complete you can selectively overwrite each subsection of file type: Changed, Added, and Removed.

In this example we pack up an Apache websever and Postgresql database.
1. `pacback -c 1 -f -d /var/www /etc/httpd /var/lib/postgres/data`
2. `pacman -Syu`
3. `pacback -rb 1` 

![Pacback Saving App Data]()

### Orchistrated Updates For Production Systems
***Coming Soon*** 


------------------------


## Pacback's Design:
Pacback is written entirely in python3 and attempts to implement most features natively. This means fast performance and minimal pip packages (only python-tqdm is used). Since its release, Pacback has been aggressively streamlined, resulting in short run times. Costly string comparisons and regex filters have been multi-threaded, which has greatly reduced each session's overall runtime. On my laptop, generating a light restore point usually takes ~180 milliseconds. Rolling back to the same restore point is a lengthier process, but still only clocks in at 700-900 milliseconds.

Pacback offers several utilities that primarily use two core restore methods: **Full and Light Restore Points.** These two types of restore points offer different drawbacks and advantages as you will see below.

### Light Restore Points
By default, Pacback creates a Light Restore Point which consists of only a .meta file. When you fall back on this restore point, Pacback will search your file system looking for old versions specified in the .meta file. If you have not cleared your cache or are rolling back a recent upgrade, Light Restore Points provide extremely fast and effective rollbacks. 

**Light Restore Point Advantages:**
 - Light RP's are Extremely Small (~25KB)
 - Generating a Light RP's is Fast (~200 milliseconds)
 - Low Overhead Means No Impact on Pacman Upgrade Times

**Light Restore Point Disadvantages:**
 - Light RP's Will Fail to Provide Real Value If Old Package Versions Are Removed (aka. paccahe -r)

### Full Restore Points
When a Full Restore Point is used, Pacback searches through your file system looking for each package version installed. Pacback then creates a Restore Point folder which contains a hardlink to each compiled package installed on the system at the time of its creation, along with any additional files the user specifies.  Since each package is a hardlinked to an inode, a package can be referenced an infinite number of times without duplication. A package will not be fully deleted from the system until all references to the inode are removed. This also provides light restore points additional resilience as they will automatically search full restore points for the packages they need.

![https://i.imgur.com/eikZF2g.jpg](https://i.imgur.com/eikZF2g.jpg)

Full Restore Points also generate a metadata file but even if you lose or delete this file, you will still be able to run a full system rollback and Pacback will simply skip its more advanced features. When you fallback on a Full Restore Point, Pacback runs its normal package checks giving you the ability rollback packages and remove any new packages added since its creation. Once this is complete, if you have any config files saved, Pacback with checksum each file and compare it to your file system. Pacback will then let you selectively overwrite each subsection of file type: Changed, Added, and Removed.

**Full Restore Point Advantages:**
 - Full RP's Are 100% Self Contained
 - Adding Custom Directories Allows for the Rollback of Config Files Associated with New Versions
 - Full RP's Ensure That Packages Are Not Prematurely Removed
 - Provides Light Restore Points Additional Resilience

**Full Restore Point Disadvantages:**
- Hardlinking Packages Can Take A Long Time (~15-25 seconds)
- Full RP's Don't Protect Against Inode Corruption


------------------


## Metadata Files
Restore Point metadata files contain information in a human readable format about packages installed at the time of its creation along with other information. This information is used by Pacback to restore older versions of packages and provide general information about the Restore Point. Each meta data file will look something like this:

> ====== Pacback RP #02 ======  
Pacback Version: 2.0.0
Date Created: 2020/03/04
Time Created: 22:37:54
Packages Installed: 272
RP Type: Light RP
>
>======= Pacman List ========  
a52dec 0.7.4-10  
aarch64-linux-gnu-binutils 2.33.1-1  
aarch64-linux-gnu-gcc 9.2.0-1  
aarch64-linux-gnu-glibc 2.30-1  
aarch64-linux-gnu-linux-api-headers 4.20-1


------------------


## Feature Path, Known Bugs, Issues, and Limitations
This list is likely to have many changes and edits as new versions are released. Please read this carefully when updating versions or deploying pacback to new systems.
If you run into any errors or are about to submit a bug, please check your log file located in '/var/log/pacback.log'.

### Issues:
- **Pacback Skips Checksumming Files over 5GB.** - This is done for several reasons. First, Python sucks at reading large files. In my testing, checksumming took 30x-50x longer compared to the terminal equivalent. Second, storing and comparing large files is not really Pacback's use-case. Packaging directories into a restore point is intended for saving the state of potentially thousands of small configuration files, not large archives or databases. 

- **Pacback Creates Missing Directories as Root.** - Currently files are copied out of the restore point with the exact same permissions they went in with. The issue here is the creation of missing directories. When Pacback creates these directories the original permissions are not copied. 

### Feature Path:
- [x] Version Checking
- [x] Version Migration
- [x] Improved Cache and Restore Point Cleaning
- [x] Pacman Hook
- [x] Improved Searches for Individual Packages
- [x] Internal Logging
- [x] PEP8 Compliance(ish)
- [x] Multi-Threaded Package Searches and Filtering
- [x] Linux Filesystem Hierarchy Compliance
- [x] Fix Checksumming
- [x] AUR Package
- [x] Improved Internal Documentation
- [x] Add Session and Snapshot Cooldown Lock
- [x] Retain Multiple Snapshots
- [x] Better Color Output
- [ ] Add --diff Command to Compare Two RPs
- [ ] Improved SigInt (Ctrl-C) Handling
- [ ] Human Readable TimeLine for SnapShot Changes
- [ ] Support for Fetching Single Non-Cached Package Versions
- [ ] Orchestrated Upgrades for Production Systems
- [ ] Support for Fetching Multiple Non-Cached Package Versions
