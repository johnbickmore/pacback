#! /usr/bin/env python3
import os
import re
import itertools
import subprocess
import sys
import multiprocessing as mp
import python_scripts as PS


#<#><#><#><#><#><#>#<#>#<#
#<># Utils For Other Funcs
#<#><#><#><#><#><#>#<#>#<#


def max_threads(thread_cap):
    cores = os.cpu_count()
    if cores >= thread_cap:
        return thread_cap
    else:
        return cores


def find_pkgs_in_dir(path):
    cache = {f for f in PS.Search_FS(path, 'set')
             if f.endswith(".pkg.tar.xz") or f.endswith(".pkg.tar.zst")}
    return cache


def first_pkg_path(pkgs, fs_list):
    paths = list()
    for pkg in pkgs:
        for f in fs_list:
            if f.split('/')[-1] == pkg:
                paths.append(f)
                break
    return paths


def search_pkg_chunk(search, fs_list):
    pkgs = list()
    for f in fs_list:
        if re.findall(search, f.lower()):
            pkgs.append(f)
    return pkgs


def trim_pkg_list(pkg_list):
    '''Removes prefix dir and x86_64.pkg.tar.zsd suffix.'''
    pkg_split = {pkg.split('/')[-1] for pkg in pkg_list}
    pkg_split = {'-'.join(pkg.split('-')[:-1]) for pkg in pkg_split}
    return pkg_split


def find_in_meta(meta_data, key):
    for m in meta_data:
        if m.split(':')[0] == key:
            value = ':'.join(m.split(':')[1:]).strip()
            return value
    return False


def abort_with_log(func, output, message, log_file):
    PS.Write_To_Log(func, output, log_file)
    PS.End_Log(func, log_file)
    PS.prError(message)
    sys.exit()


def require_root(log_file):
    '''Abort if not root.'''
    if PS.Am_I_Root() is True:
        PS.Start_Log('PacbackMain', log_file)
        PS.Write_To_Log('RootCheck', 'Passed Root Check', log_file)
        return
    else:
        sys.exit('Critical Error: Must Be Run As Root!')


def sig_catcher(log_file, signum, frame):
    if os.path.exists('/tmp/pacback_session_lock'):
        os.system('rm /tmp/pacback_session_lock')
        PS.Write_To_Log('SIGINT', 'Cleaned Session Lock', log_file)
    abort_with_log('SIGINT', 'Caught SIGINT ' + str(signum), '\n Attempting Clean Exit', log_file)


def shift_snapshots(max_ss, rp_paths, log_file):
    PS.Write_To_Log('ShiftSS', 'Shifting SnapShots Forward With a Max of ' + str(max_ss), log_file)
    for x in range((max_ss - 1), -1, -1):
        m_path = rp_paths + '/ss' + str(x).zfill(2) + '.meta'
        if os.path.exists(m_path):
            os.system('sed -i s/#' + str(x).zfill(2) + '/#' + str(x + 1).zfill(2) + '/ ' + m_path)
            os.system('mv ' + m_path + ' ' + rp_paths + '/ss'+ str(x + 1).zfill(2) + '.meta')
    PS.Write_To_Log('ShiftSS', 'All SnapShots Shifted Forward', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Pacman Utils
#<#><#><#><#><#><#>#<#>#<#


def pacman_Q():
    '''Writes the output into /tmp, reads file, then removes file.'''
    os.system("pacman -Q > /tmp/pacman_q.meta")
    ql = PS.Read_List('/tmp/pacman_q.meta', typ='set')
    PS.RM_File('/tmp/pacman_q.meta', sudo=True)
    return ql


def fetch_paccache(rp_paths, log_file):
    '''Always returns a unique list of pkgs found on the file sys.'''
    thread_cap = 4

    # Searches File System For Packages
    pacman_cache = find_pkgs_in_dir('/var/cache/pacman/pkg')
    root_cache = find_pkgs_in_dir('/root/.cache')
    pacback_cache = find_pkgs_in_dir(rp_paths)
    user_cache = set()
    users = os.listdir('/home')

    for u in users:
        u_pkgs = find_pkgs_in_dir('/home/' + u + '/.cache')
        user_cache = user_cache.union(u_pkgs)

    fs_list = pacman_cache.union(root_cache, pacback_cache, user_cache)
    PS.Write_To_Log('FetchPaccache', 'Searched ALL Package Cache Locations', log_file)

    unique_pkgs = PS.Trim_Dir(fs_list)
    if len(fs_list) != len(unique_pkgs):
        PS.prWarning('Filtering Duplicate Packages...')

        chunk_size = int(round(len(unique_pkgs) / max_threads(thread_cap), 0)) + 1
        unique_pkgs = list(f for f in unique_pkgs)
        chunks = [unique_pkgs[i:i + chunk_size] for i in range(0, len(unique_pkgs), chunk_size)]

        with mp.Pool(processes=max_threads(thread_cap)) as pool:
            new_fs = pool.starmap(first_pkg_path, zip(chunks, itertools.repeat(fs_list)))
            new_fs = set(itertools.chain(*new_fs))

        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(new_fs)) + ' Unique Cache Packages', log_file)
        return new_fs

    else:
        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(fs_list)) + ' Cached Packages', log_file)
        return fs_list


def search_paccache(pkg_list, fs_list, log_file):
    '''Searches cache for matching pkg versions and returns results.'''
    thread_cap = 4

    # Combing package names into one term provides much faster results
    PS.Write_To_Log('SearchPaccache', 'Started Search for ' + str(len(pkg_list)) + ' Packages', log_file)
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list)))
    chunk_size = int(round(len(fs_list) / max_threads(thread_cap), 0)) + 1
    fs_list = list(f for f in fs_list)
    chunks = [fs_list[i:i + chunk_size] for i in range(0, len(fs_list), chunk_size)]

    with mp.Pool(processes=max_threads(thread_cap)) as pool:
        found_pkgs = pool.starmap(search_pkg_chunk, zip(itertools.repeat(bulk_search), chunks))
        found_pkgs = set(itertools.chain(*found_pkgs))

    PS.Write_To_Log('SearchPaccache', 'Found ' + str(len(found_pkgs)) + ' OUT OF ' + str(len(pkg_list)) + ' Packages', log_file)
    return found_pkgs


#<#><#><#><#><#><#>#<#>#<#
#<># Session Management
#<#><#><#><#><#><#>#<#>#<#


def fork_hook_lock(cooldown, log_file):
    subprocess.Popen('touch /tmp/pacback_hook_lock && sleep ' + str(cooldown) + ' && rm /tmp/pacback_hook_lock', shell=True)
    PS.Write_To_Log('HookLock', 'Spawned ' + str(cooldown) + ' Second Hook Cooldown Lock', log_file)


def fork_session_lock(log_file):
    pid = os.getpid()
    os.system('touch /tmp/pacback_session_lock')
    subprocess.Popen('while ps -p ' + str(pid) + ' > /dev/null; do sleep 1; done; rm /tmp/pacback_session_lock', shell=True)
    PS.Write_To_Log('SessionLock', 'Spawned Session Lock', log_file)


def check_lock(typ, log_file):
    if typ == 'hook':
        if os.path.exists('/tmp/pacback_hook_lock'):
            abort_with_log('HookLock', 'Aborting: HookLock is Still Cooling Down!',
                              'Aborting: HookLock is Still Cooling Down!', log_file)
        else:
            PS.Write_To_Log('HookLock', 'Passed Hook Lock Check', log_file)

    elif typ == 'session':
        if os.path.exists('/tmp/pacback_session_lock'):
            abort_with_log('SessionLock', 'Aborting: Pacback Already Has An Active Session Lock',
                              'Aborting: Pacback Already Has An Active Session Lock', log_file)
        else:
            PS.Write_To_Log('SessionLock', 'Passed Session Lock Check', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Pacman Hook
#<#><#><#><#><#><#>#<#>#<#


def pacman_hook(install, log_file):
    '''Installs or removes a standard alpm hook in /etc/pacman.d/hooks
    Runs as a PreTransaction hook during every upgrade.'''

    if install is True:
        PS.Write_To_Log('InstallHook', 'Starting Hook Install Process', log_file)
        PS.MK_Dir('/etc/pacman.d/hooks', sudo=False)
        PS.Uncomment_Line_Sed('HookDir', '/etc/pacman.conf', sudo=False)
        hook = ['[Trigger]',
                'Operation = Upgrade',
                'Type = Package',
                'Target = *',
                '',
                '[Action]',
                'Description = Pre-Upgrade Pacback Hook',
                'Depends = pacman',
                'When = PreTransaction',
                'Exec = /usr/bin/pacback --hook']
        PS.Export_List('/etc/pacman.d/hooks/pacback.hook', hook)
        PS.prSuccess('Pacback Hook is Now Installed!')
        PS.Write_To_Log('InstallHook', 'Installed Pacback Hook Successfully', log_file)

    elif install is False:
        PS.Write_To_Log('RemoveHook', 'Starting Hook Removal Process', log_file)
        PS.RM_File('/etc/pacman.d/hooks/pacback.hook', sudo=False)
        PS.Write_To_Log('RemoveHook', 'Removed Pacback Hook Successfully', log_file)
        PS.prSuccess('Pacback Hook Removed!')


#<#><#><#><#><#><#>#<#>#<#
#<># Version Control
#<#><#><#><#><#><#>#<#>#<#


def compare_version(current_version, rp_path, meta_exists, meta, log_file):
    if meta_exists is False:
        PS.Write_To_Log('VersionControl', 'Restore Point is Missing MetaData', log_file)

    elif meta_exists is True:
        target_version = find_in_meta(meta, 'Pacback Version')

        # Parse version into vars
        cv_M = int(current_version.split('.')[0])
        cv_m = int(current_version.split('.')[1])
        cv_p = int(current_version.split('.')[2])
        ####
        tv_M = int(target_version.split('.')[0])
        tv_m = int(target_version.split('.')[1])
        tv_p = int(target_version.split('.')[2])

        if current_version != target_version:
            PS.Write_To_Log('VersionControl', 'Current Version ' + current_version + ' Miss-Matched With ' + target_version, log_file)
        else:
            PS.Write_To_Log('VersionControl', 'Both Versions Match ' + current_version, log_file)

        # Check for Full RP's Created Before V1.5
        if tv_M == 1 and tv_m < 5:
            PS.prError('Full Restore Points Generated Before V1.5.0 Are No Longer Compatible With Newer Versions of Pacback!')
            PS.Write_To_Log('VersionControl', 'Detected Restore Point Version Generated > V1.5', log_file)
            PS.Abort_With_Log('VersionControl', 'User Exited Upgrade',
                              'Aborting!', log_file)
