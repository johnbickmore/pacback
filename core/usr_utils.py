#! /usr/bin/env python3
import os
import re
import datetime as dt
import pac_utils as pu
import python_scripts as PS


#<#><#><#><#><#><#>#<#>#<#
#<># Manual Package Search
#<#><#><#><#><#><#>#<#>#<#


def user_pkg_search(search_pkg, cache):
    '''Provides more accurate searches for single pkg names without a version.'''
    pkgs = pu.trim_pkg_list(cache)
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


#<#><#><#><#><#><#>#<#>#<#
#<># Print RP Info
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
        PS.prError('Restore Point #' + num + ' Was NOT Found!')


def list_all_rps(rp_paths):
    files = {f for f in PS.Search_FS(rp_paths, 'set') if f.endswith(".meta")}
    restore_points = list()
    snapshots = list()
    max_line_length = 0

    for f in files:
        meta = PS.Read_List(f)

        num = str(f[-7] + f[-6])
        date = pu.find_in_meta(meta, 'Date Created')
        #  time = pu.find_in_meta(meta, 'Time Created')
        pkgs = pu.find_in_meta(meta, 'Packages Installed')
        typ = pu.find_in_meta(meta, 'RP Type')
        label = pu.find_in_meta(meta, 'Label')

        if typ == 'SnapShot':
            op = 'SS #' + num
        else:
            op = 'RP #' + num

        if typ == 'Full RP':
            op = op + ' | Type: ' + typ + ' '
        elif typ == 'Light RP':
            op = op + ' | Type: ' + typ
        elif typ == 'SnapShot':
            op = op + ' | Type: ' + typ
        else:
            op = op + ' | Type: Unknown '

        if date:
            op = op + ' | Date: ' + date

        #  if time:
            #  op = op + ' ' + time
        #  else:
            #  op = op + '         '

        if pkgs:
            op = op + ' | Packages: ' + pkgs.zfill(4)

        if label:
            op = op + ' | Label: ' + label.upper()
        else:
            op = op + ' | Label: None'

        if typ == 'SnapShot':
            snapshots.append(op)
        else:
            restore_points.append(op)

        if len(op) > max_line_length:
            max_line_length = len(op)

    rps = sorted(restore_points)
    sss = sorted(snapshots)

    for o in rps:
        PS.prBold(o)
    if len(rps) > 0 and len(sss) > 0:
        print('=' * max_line_length)
    for x in sss:
        #  PS.prBold(x)
        print(x)


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
            target_date = pu.find_in_meta(meta, 'Date Created')

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
