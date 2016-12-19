#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Donne des informations de sécurité sur un fichier windows

Récupéré sur http://grokbase.com/t/python/python-win32/051wwq1aw3/folder-permissions,
http://www.programcreek.com/python/example/52870/win32security.GetFileSecurity pour
la fontion get_owner,
http://stackoverflow.com/questions/26465546/how-to-authorize-deny-write-access-to-a-directory-on-windows-using-python
pour la fonction remove_perm
"""
#
import win32security
import os

All_perms = {
    1: "ACCESS_READ",  # 0x00000001
    2: "ACCESS_WRITE",  # 0x00000002
    4: "ACCESS_CREATE",  # 0x00000004
    8: "ACCESS_EXEC",  # 0x00000008
    16: "ACCESS_DELETE",  # 0x00000010
    32: "ACCESS_ATRIB [sic]",  # 0x00000020
    64: "ACCESS_PERM",  # 0x00000040
    32768: "ACCESS_GROUP",  # 0x00008000
    65536: "DELETE",  # 0x00010000
    131072: "READ_CONTROL",  # 0x00020000
    262144: "WRITE_DAC",  # 0x00040000
    524288: "WRITE_OWNER",  # 0x00080000
    1048576: "SYNCHRONIZE",  # 0x00100000
    16777216: "ACCESS_SYSTEM_SECURITY",  # 0x01000000
    33554432: "MAXIMUM_ALLOWED",  # 0x02000000
    268435456: "GENERIC_ALL",  # 0x10000000
    536870912: "GENERIC_EXECUTE",  # 0x20000000
    1073741824: "GENERIC_WRITE",  # 0x40000000
    65535: "SPECIFIC_RIGHTS_ALL",  # 0x0000ffff
    983040: "STANDARD_RIGHTS_REQUIRED",  # 0x000f0000
    2031616: "STANDARD_RIGHTS_ALL",  # 0x001f0000
}

Typical_perms = {
    2032127: "Full Control(All)",
    1179817: "Read(RX)",
    1180086: "Add",
    1180095: "Add&Read",
    1245631: "Change"
}


#   -------------------------------------------------------------------------------
def get_owner(file):
    r""" Return the name of the owner of this file or directory.

    This follows symbolic links.

    On Windows, this returns a name of the form ur'DOMAIN\User Name'.
    On Windows, a group can own a file or directory.
    """
    if os.name == 'nt':
        if win32security is None:
            raise Exception("path.owner requires win32all to be installed")

        desc = win32security.GetFileSecurity(file, win32security.OWNER_SECURITY_INFORMATION)
        sid = desc.GetSecurityDescriptorOwner()
        try:
            account, domain, typecode = win32security.LookupAccountSid(None, sid)
        except:
            domain = 'Domaine'
            account = '%s' % sid
        return domain + u'\\' + account
    else:
        if pwd is None:
            raise NotImplementedError("path.owner is not implemented on this platform.")
        st = file.stat()
        return pwd.getpwuid(st.st_uid).pw_name


#   -----------------------------------------------------------------------
def fileperm_get_perms(file):
    all_perms = {}
    mask = win32security.OWNER_SECURITY_INFORMATION | win32security.GROUP_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    sd = win32security.GetFileSecurity(file, mask)
    ownersid = sd.GetSecurityDescriptorOwner()
    dacl = sd.GetSecurityDescriptorDacl()
    count = dacl.GetAceCount()
    for i in range(count):
        ace = dacl.GetAce(i)
        #   ace[0][0] = 1 signifie refus
        try:
            user, domain, int = win32security.LookupAccountSid(None, ace[2])
            all_perms[domain + "\\" + user] = (ace[1], ace[0][0])
        except:
            all_perms['Domaine\\%s' % ace[2]] = (ace[1], ace[0][0])
    return all_perms


#   -----------------------------------------------------------------------
def get_mask(mask):
    a = 47483648

    #   if Typical_perms.has_key(mask):
    if mask in Typical_perms:
        return Typical_perms[mask]
    else:
        result = ''
        while a >> 1:
            a = a >> 1
            masked = mask & a
            if masked:
                if masked in All_perms and All_perms[masked] not in result:
                    result = All_perms[masked] + ':' + result
        return result


#   -----------------------------------------------------------------------
def get_perm(file):
    perm_list = []
    all_perms = fileperm_get_perms(file)
    for (domain_id, perm) in all_perms.items():
        mask = perm[0]
        type_perm = 'REFUS' if perm[1] == 1 else ''
        sys_id = domain_id.split('\\')[1]
        #   sys_id = str(sys_id)
        mask_name = get_mask(mask)
        perm_list.append([sys_id, mask_name, type_perm])
    perm_list.sort()

    return perm_list


#   -----------------------------------------------------------------------
def remove_perm(file, *users, verbose=False):
    """
    Inspiré de http://stackoverflow.com/questions/26465546/how-to-authorize-deny-write-access-to-a-directory-on-windows-using-python
    Syntaxe : 
        remove_perm('file', 'u1', 'u2', ..., 'un', verbose=x)
        OU
        remove_perm('fil', *['u1', 'u2', ..., 'un'], verbose=x)
        OU
        remove_perm('fil', *('u1', 'u2', ..., 'un'), verbose=x)
    """
    
    mask = win32security.OWNER_SECURITY_INFORMATION | win32security.GROUP_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    sd = win32security.GetFileSecurity(file, mask)
    ownersid = sd.GetSecurityDescriptorOwner()
    dacl = sd.GetSecurityDescriptorDacl()
    count = dacl.GetAceCount()
    a_supprimer = []
    #   Faire une suppression directe dans une liste qu'on parcourt...
    for i in range(count):
        ace = dacl.GetAce(i)
        try:
            user, domain, int = win32security.LookupAccountSid(None, ace[2])
        except:
            user = ace[2]

        if user.lower() in liste_users:
            if verbose:
                print('On va supprimer %s pour %s' % (userid, file))
            a_supprimer.append(i)

    for i in a_supprimer:
        dacl.DeleteAce(i)

    if a_supprimer:
        sd.SetSecurityDescriptorDacl(1, dacl, 0)   # may not be necessary
        win32security.SetFileSecurity(file, win32security.DACL_SECURITY_INFORMATION, sd)

#   -----------------------------------------------------------------------
