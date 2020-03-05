#! /usr/bin/env python3
import os
import re
import itertools
import subprocess
import sys
import datetime as dt
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
    return ""


def abort_with_log(func, output, message, log_file):
    PS.Write_To_Log(func, output, log_file)
    PS.End_Log(func, log_file)
    PS.prError(message)
    sys.exit()


def require_root(log_file):
    '''Abort if not root.'''
    if PS.Am_I_Root() is True:
        PS.Write_To_Log('RootCheck', 'Passed Root Check', log_file)
        return
    else:
        sys.exit('Critical Error: Must Be Run As Root!')


def sig_catcher(log_file, signum, frame):
    if os.path.exists('/tmp/pacback_session_lock'):
        os.system('rm /tmp/pacback_session_lock')
        PS.Write_To_Log('SIGINT', 'Cleaned Session Lock', log_file)
    abort_with_log('SIGINT', 'Caught SIGINT ' + str(signum), '\n Attempting Clean Exit', log_file)


#<#><#><#><#><#><#>#<#>#<#
#<># Session State Management
#<#><#><#><#><#><#>#<#>#<#


def spawn_hook_lock(cooldown, log_file):
    subprocess.Popen('touch /tmp/pacback_hook_lock && sleep ' + str(cooldown) + ' && rm /tmp/pacback_hook_lock', shell=True)
    PS.Write_To_Log('HookLock', 'Spawned ' + str(cooldown) + ' Second Hook Cooldown Lock', log_file)


def spawn_session_lock(log_file):
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
#<># Pacman Utils
#<#><#><#><#><#><#>#<#>#<#


def user_pkg_search(search_pkg, cache):
    '''Provides more accurate searches for single pkg names without a version.'''
    pkgs = trim_pkg_list(cache)
    found = set()

    for p in pkgs:
        r = re.split("\d+-\d+|\d+(?:\.\d+)+|\d:\d+(?:\.\d+)+", p)[0]
        if r.strip()[-1] == '-':
            x = r.strip()[:-1]
        else:
            x = r
        if re.fullmatch(re.escape(search_pkg.lower().strip()), x):
            found.add(p)

    if not found:
        PS.prError('No Packages Found!')
        if PS.YN_Frame('Do You Want to Extend the Regex Search?') is True:
            for p in pkgs:
                if re.findall(re.escape(search_pkg.lower().strip()), p):
                    found.add(p)

    return found


def pacman_Q():
    '''Writes the output into /tmp, reads file, then removes file.'''
    os.system("pacman -Q > /tmp/pacman_q.meta")
    ql = PS.Read_List('/tmp/pacman_q.meta', typ='set')
    PS.RM_File('/tmp/pacman_q.meta', sudo=True)
    return ql


def fetch_paccache(rp_paths, log_file):
    '''Always returns a unique list of pkgs found on the file sys.'''

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

        chunk_size = int(round(len(unique_pkgs) / max_threads(4), 0)) + 1
        unique_pkgs = list(f for f in unique_pkgs)
        chunks = [unique_pkgs[i:i + chunk_size] for i in range(0, len(unique_pkgs), chunk_size)]

        with mp.Pool(processes=max_threads(4)) as pool:
            new_fs = pool.starmap(first_pkg_path, zip(chunks, itertools.repeat(fs_list)))
            new_fs = set(itertools.chain(*new_fs))

        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(new_fs)) + ' Unique Cache Packages', log_file)
        return new_fs

    else:
        PS.Write_To_Log('FetchPaccache', 'Returned ' + str(len(fs_list)) + ' Cached Packages', log_file)
        return fs_list


def search_paccache(pkg_list, fs_list, log_file):
    '''Searches cache for matching pkg versions and returns results.'''
    PS.Write_To_Log('SearchPaccache', 'Started Search for ' + str(len(pkg_list)) + ' Packages', log_file)

    # Combing package names into one term provides much faster results
    bulk_search = ('|'.join(list(re.escape(pkg) for pkg in pkg_list)))
    chunk_size = int(round(len(fs_list) / max_threads(4), 0)) + 1
    fs_list = list(f for f in fs_list)
    chunks = [fs_list[i:i + chunk_size] for i in range(0, len(fs_list), chunk_size)]

    with mp.Pool(processes=max_threads(4)) as pool:
        found_pkgs = pool.starmap(search_pkg_chunk, zip(itertools.repeat(bulk_search), chunks))
        found_pkgs = set(itertools.chain(*found_pkgs))

    PS.Write_To_Log('SearchPaccache', 'Found ' + str(len(found_pkgs)) + ' OUT OF ' + str(len(pkg_list)) + ' Packages', log_file)
    return found_pkgs


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
#<># RP Management
#<#><#><#><#><#><#>#<#>#<#


def print_rp_info(num, rp_paths):
    rp_meta = rp_paths + '/rp' + num + '.meta'
    if os.path.exists(rp_meta):
        meta = PS.Read_List(rp_meta)
        meta = PS.Read_Between('Pacback RP', 'Pacman List', meta, re_flag=True)
        print('============================')
        for s in meta[:-1]:
            print(s)
        print('============================')

    elif os.path.exists(rp_meta):
        PS.prError('Meta is Missing For This Restore Point!')

    else:
        PS.prError('No Restore Point #' + num + ' Was NOT Found!')


def list_all_rps(rp_paths):
    files = {f for f in PS.Search_FS(rp_paths, 'set') if f.endswith(".meta")}
    restore_points = list()
    snapshots = list()

    for f in files:
        meta = PS.Read_List(f)
        if find_in_meta(meta, 'RP Type') == 'SnapShot':
            output = 'SS #' + f[-7] + f[-6] + ' - Date: ' + find_in_meta(meta, 'Date Created') + " " + find_in_meta(meta, 'Time Created')
            output = output + ' - Packages Installed: ' + find_in_meta(meta, 'Packages Installed')
            output = output + ' - Type: ' + find_in_meta(meta, 'RP Type')
            snapshots.append(str(output))

        else:
            output = 'RP #' + f[-7] + f[-6] + ' - Date: ' + find_in_meta(meta, 'Date Created') + " " + find_in_meta(meta, 'Time Created')
            output = output + ' - Packages Installed: ' + find_in_meta(meta, 'Packages Installed')
            output = output + ' - Type: ' + find_in_meta(meta, 'RP Type')
            restore_points.append(str(output))

    rps = sorted(restore_points)
    sss = sorted(snapshots)
    for o in rps:
        PS.prSuccess(o)
    for x in sss:
        PS.prBold(x)


def remove_rp(rp_num, rp_paths, nc, log_file):
    rp = rp_paths + '/rp' + rp_num + '.meta'
    print_rp_info(rp_num, rp_paths)

    if nc is False:
        if PS.YN_Frame('Do You Want to Remove This Restore Point?') is True:
            PS.RM_File(rp, sudo=False)
            PS.RM_Dir(rp[:-5], sudo=False)
            PS.prSuccess('Restore Point Removed!')
            PS.Write_To_Log('RemoveRP', 'Removed Restore Point ' + rp_num, log_file)
        else:
            PS.Write_To_Log('RemoveRP', 'User Declined Removing Restore Point ' + rp_num, log_file)

    elif nc is True:
        PS.RM_File(rp, sudo=False)
        PS.RM_Dir(rp[:-5], sudo=False)
        PS.prSuccess('Restore Point Removed!')
        PS.Write_To_Log('RemoveRP', 'Removed Restore Point ' + rp_num, log_file)


def shift_snapshots(max_ss, rp_paths, log_file):
    PS.Write_To_Log('ShiftSS', 'Shifting SnapShots Forward With a Max of ' + str(max_ss), log_file)
    for x in range((max_ss - 1), -1, -1):
        m_path = rp_paths + '/ss' + str(x).zfill(2) + '.meta'
        if os.path.exists(m_path):
            os.system('sed -i s/#' + str(x).zfill(2) + '/#' + str(x + 1).zfill(2) + '/ ' + m_path)
            os.system('cat ' + m_path + ' > ' + rp_paths + '/ss'+ str(x + 1).zfill(2) + '.meta')
    PS.Write_To_Log('ShiftSS', 'All SnapShots Shifted Forward', log_file)



#<#><#><#><#><#><#>#<#>#<#
#<># Better Cache Cleaning
#<#><#><#><#><#><#>#<#>#<#


def clean_cache(count, rp_paths, log_file):
    '''Automated Cache Cleaning Using pacman, paccache, and pacback.'''
    PS.prWarning('Starting Advanced Cache Cleaning...')
    if PS.YN_Frame('Do You Want To Uninstall Orphaned Packages?') is True:
        os.system('sudo pacman -R $(pacman -Qtdq)')
        PS.Write_To_Log('CleanCache', 'Ran pacman -Rns $(pacman -Qtdq)', log_file)

    if PS.YN_Frame('Do You Want To Remove Old Versions of Installed Packages?') is True:
        os.system('sudo paccache -rk ' + count)
        PS.Write_To_Log('CleanCache', 'Ran paccache -rk ' + count, log_file)

    if PS.YN_Frame('Do You Want To Remove Cached Orphans?') is True:
        os.system('sudo paccache -ruk0')
        PS.Write_To_Log('CleanCache', 'Ran paccache -ruk0', log_file)

    if PS.YN_Frame('Do You Want To Check For Old Pacback Restore Points?') is True:
        PS.Write_To_Log('CleanCache', 'Started Search For Old RPs', log_file)
        metas = PS.Search_FS(rp_paths, 'set')
        rps = {f for f in metas if f.endswith(".meta")}

        for m in rps:
            rp_num = m.split('/')[-1]
            # Find RP Create Date in Meta File
            meta = PS.Read_List(m)
            target_date = find_in_meta(meta, 'Date Created')

            # Parse and Format Dates for Compare
            today = dt.datetime.now().strftime("%Y/%m/%d")
            t_split = list(today.split('/'))
            today_date = dt.date(int(t_split[0]), int(t_split[1]), int(t_split[2]))
            o_split = list(target_date.split('/'))
            old_date = dt.date(int(o_split[0]), int(o_split[1]), int(o_split[2]))

            # Compare Days
            days = (today_date - old_date).days
            if days > 180:
                PS.prWarning(m.split('/')[-1] + ' Is Over 180 Days Old!')
                if PS.YN_Frame('Do You Want to Remove This Restore Point?') is True:
                    PS.RM_File(m, sudo=True)
                    PS.RM_Dir(m[:-5], sudo=True)
                    PS.prSuccess('Restore Point Removed!')
                    PS.Write_To_Log('CleanCache', 'Removed RP ' + rp_num, log_file)
            PS.prSuccess(rp_num + ' Is Only ' + str(days) + ' Days Old!')
            PS.Write_To_Log('CleanCache', 'RP ' + rp_num + ' Was Less Than 180 Days 0ld', log_file)
