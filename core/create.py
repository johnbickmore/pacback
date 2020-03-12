#! /usr/bin/env python3
import re
import os
import tarfile
import tqdm
import datetime as dt
import python_scripts as PS
import pac_utils as pu


#<#><#><#><#><#><#>#<#>#<#
#<># Create
#<#><#><#><#><#><#>#<#>#<#


def create(typ, version, rp_num, rp_full, dir_list, no_confirm, label, rp_paths, log_file):
    PS.Write_To_Log('Create' + typ.upper(), 'Reached Create' + typ.upper(), log_file)
    # Fail Safe for New Users
    if os.path.exists(rp_paths) is False:
        PS.MK_Dir('/var/lib/pacback', sudo=False)
        PS.MK_Dir(rp_paths, sudo=False)
        PS.Write_To_Log('Create' + typ.upper(), 'Created Base RP Folder in /var/lib', log_file)

    # Set Base Vars
    rp_num = str(rp_num).zfill(2)
    rp_path = rp_paths + '/' + typ + rp_num
    rp_tar = rp_path + '/' + typ + rp_num + '_dirs.tar'
    rp_meta = rp_path + '.meta'
    found_pkgs = set()
    pac_size = 0

    # Check for Existing Restore Points
    if os.path.exists(rp_path) or os.path.exists(rp_meta):
        if no_confirm is False:
            if int(rp_num) != 0:
                PS.prWarning('Restore Point #' + rp_num + ' Already Exists!')
                if PS.YN_Frame('Do You Want to Overwrite It?') is False:
                    pu.abort_with_log('CreateRP', 'User Aborted Overwrite of RP #' + rp_num, 'Aborting!', log_file)

        PS.RM_File(rp_meta, sudo=False)
        PS.RM_Dir(rp_path, sudo=False)
        PS.Write_To_Log('CreateRP', 'Removed Previous RP #' + rp_num + ' During Creation', log_file)

    ####################
    # Full Restore Point
    ####################
    if rp_full is True:
        PS.Write_To_Log('CreateRP', 'Building RP #' + rp_num + ' As Full RP', log_file)
        PS.prBold('Building Full Restore Point...')

        # Set Vars For Full RP
        dir_size = 0
        rp_files = set()
        pac_cache = rp_path + '/pac_cache'

        PS.prBold('Retrieving Current Packages...')
        pkg_search = PS.Replace_Spaces(pu.pacman_Q())

        # Search File System for Pkgs
        PS.prWarning('Bulk Scanning for ' + str(len(pkg_search)) + ' Packages...')
        found_pkgs = pu.search_paccache(pkg_search, pu.fetch_paccache(rp_paths, log_file), log_file)
        pac_size = PS.Size_Of_Files(found_pkgs)

        # Ask About Missing Pkgs
        if len(found_pkgs) != len(pkg_search):
            PS.Write_To_Log('CreateRP', 'Not All Packages Where Found', log_file)
            if int(rp_num) != 0:
                if no_confirm is False:
                    pkg_split = pu.trim_pkg_list(found_pkgs)
                    PS.prError('The Following Packages Where NOT Found!')
                    for pkg in set(pkg_search - pkg_split):
                        PS.prWarning(pkg + ' Was NOT Found!')
                    if PS.YN_Frame('Do You Still Want to Continue?') is False:
                        pu.abort_with_log('CreateRP', 'User Aborted Due to Missing Pkgs', 'Aborting!', log_file)

        # HardLink Packages to RP
        PS.MK_Dir(rp_path, sudo=False)
        PS.MK_Dir(pac_cache, sudo=False)
        for pkg in tqdm.tqdm(found_pkgs, desc='Hardlinking Packages to Pacback RP'):
            os.system('sudo ln ' + pkg + ' ' + pac_cache + '/' + pkg.split('/')[-1])
        PS.Write_To_Log('CreateRP', 'HardLinked ' + str(len(found_pkgs)) + ' Packages', log_file)

        # Find Custom Files for RP
        if dir_list:
            PS.Write_To_Log('CreateRP', 'User Defined Custom RP Files', log_file)
            # Find and Get Size of Custom Files
            for d in dir_list:
                for f in PS.Search_FS(d, 'set'):
                    try:
                        dir_size += os.path.getsize(f)
                    except Exception:
                        OSError
                    rp_files.add(f)

            # Pack Custom Folders Into a Tar
            with tarfile.open(rp_tar, 'w') as tar:
                for f in tqdm.tqdm(rp_files, desc='Adding Dir\'s to Tar'):
                    tar.add(f)
            PS.Write_To_Log('CreateRP', 'Tar Created For Custom RP Files', log_file)

            # Compress Custom Files If Added Larger Than 1GB
            if dir_size > 1073741824:
                PS.prWarning('Compressing Restore Point Files...')
                if any(re.findall('pigz', l.lower()) for l in pkg_search):
                    os.system('pigz ' + rp_tar + ' -f')
                else:
                    PS.GZ_C(rp_tar, rm=True)
                PS.Write_To_Log('CreateRP', 'Compressed Custom Files RP Tar', log_file)

    elif rp_full is False:
        if typ == 'rp':
            PS.Write_To_Log('CreateRP', 'Building RP #' + rp_num + ' As A Light RP', log_file)
            if len(dir_list) > 0:
                pu.abort_with_log('CreateRP', 'Custom Dirs Are Not Supported By LightRP',
                                  'Light Restore Points DO NOT Support Custom Dirs! Please Use The `-f` Flag', log_file)
            PS.prBold('Building Light Restore Point...')
        elif typ == 'ss':
            PS.Write_To_Log('CreateSS', 'Building SnapShot', log_file)

    #########################
    # Generate Meta Data File
    #########################
    current_pkgs = pu.pacman_Q()
    meta_list = ['====== Pacback ' + typ.upper() + ' #' + rp_num + ' ======',
                 'Pacback Version: ' + version,
                 'Date Created: ' + dt.datetime.now().strftime("%Y/%m/%d"),
                 'Time Created: ' + dt.datetime.now().strftime("%H:%M:%S"),
                 'Packages Installed: ' + str(len(current_pkgs))]

    if rp_full is True:
        meta_list.append('RP Type: Full RP')
        meta_list.append('Packages in RP: ' + str(len(found_pkgs)))
        meta_list.append('Size of Packages in RP: ' + PS.Convert_Size(pac_size))
    elif rp_full is False:
        if typ == 'rp':
            meta_list.append('RP Type: Light RP')
        elif typ == 'ss':
            meta_list.append('RP Type: SnapShot')

    if label:
        meta_list.append('Label: ' + label)

    if len(dir_list) != 0:
        meta_list.append('Dirs File Count: ' + str(len(rp_files)))
        meta_list.append('Dirs Total Size: ' + PS.Convert_Size(dir_size))
        meta_list.append('')
        meta_list.append('========= Dir List =========')
        for d in dir_list:
            meta_list.append(d)

    meta_list.append('')
    meta_list.append('======= Pacman List ========')
    for pkg in current_pkgs:
        meta_list.append(pkg)

    # Export Final Meta Data File
    PS.Export_List(rp_meta, meta_list)
    PS.Write_To_Log('Create' + typ.upper(), typ.upper() + ' #' + rp_num + ' Was Successfully Created', log_file)
    PS.Write_To_Log('Create' + typ.upper(), 'Exited Create' + typ.upper(), log_file)
    if typ == 'ss':
        PS.prSuccess('SnapShot Successfully Created!')
    elif typ == 'rp':
        PS.prSuccess('Restore Point #' + rp_num + ' Successfully Created!')


def snapshot(version, max_snapshots, hook_cooldown, rp_paths, log_file):
    pu.check_lock('hook', log_file)
    pu.shift_snapshots(max_snapshots, rp_paths, log_file)
    create('ss', version, 0, False, [], True, False, rp_paths, log_file)
    pu.fork_hook_lock(hook_cooldown, log_file)


def restore_point(version, rp_num, rp_full, dir_list, no_confirm, label, rp_paths, log_file):
    create('rp', version, rp_num, rp_full, dir_list, no_confirm, label, rp_paths, log_file)
