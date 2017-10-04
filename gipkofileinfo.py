#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
    Donne des informations de sécurité sur un fichier windows.

    Syntaxe : liste_droits = get_perm(nom_fichier)
    Chaque élément de la liste retournée est une liste contenant dans cet ordre :
    - Nom de l'utilisateur ou du groupe
    - Droit d'accès textuel ("read", "change", "full control" etc)
    - Type du droit précédent : "" si droit accordé, "REFUS" sinon
    - Droit d'accès sous forme numérique (masque) tel qu'il est renvoyé par le système
    - Type du droit tel qu'il est renvoyé par le système, 0 = accordé, 1 = refusé.
        Sachant que le refus est prioritaire.
    - Information sur l'héritage et la propagation. (Pas très clair aujourd'hui)

    Récupéré sur http://grokbase.com/t/python/python-win32/051wwq1aw3/folder-permissions,
    http://www.programcreek.com/python/example/52870/win32security.GetFileSecurity pour
    la fontion get_owner,
    http://stackoverflow.com/questions/26465546/how-to-authorize-deny-write-access-to-a-directory-on-windows-using-python
    pour la fonction remove_perm

    Version 2 2017-01-10
        La version 1 renvoyait les résultats interprétés.
        Comme ça peut être utile la version 2 renvoie AUSSI les résultats bruts en éléments 3, 4 et 5 de la liste

    Version 2.1 2017-01-24
        La fonction get_perm prend en argument optionnel un dictionnaire contenant deux dictionnaires :
        "users" et "groups".
        Si cet argument est renseigné on ajoute au nom d'utilisateur l'information utilisateur ou groupe.
        Ça permet de trier les permissions et d'afficher les groupes et les utilisateurs individuels séparément.

    Version 2.2 2017-02-21
        Ajouté la fonction add_perm.

    Version 2.3 2017-05-12
        Ajouté les fonctions get_tree_size, affichageHumain et dateISO.

    Version 2.4 2017-06-27
        Ajouté des fonctions de gestion des dates de fichier : get_file_dates, print_file_dates
        et set_file_dates pour pouvoir corriger des fichiers et remettre ensuite (à la main)
        sa date de modif originale.

"""
#
import win32security
import os
import logging
import traceback
import locale
import datetime

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
    1245631: "Change",
    1048609: "Walk Dir"
}

FULL_CONTROL = 2032127
READ = 1179817
CHANGE = 1245631
WALK_DIR = 1048609

VERSION = '2.4'


#   -------------------------------------------------------------------------------
def get_owner(file):
    logger = logging.getLogger()
    r""" Return the name of the owner of this file or directory.

    This follows symbolic links.

    On Windows, this returns a name of the form ur'DOMAIN\User Name'.
    On Windows, a group can own a file or directory.
    """
    if os.name == 'nt':
        if win32security is None:
            raise Exception("path.owner requires win32all to be installed")

        try:
            desc = win32security.GetFileSecurity(file, win32security.OWNER_SECURITY_INFORMATION)
            sid = desc.GetSecurityDescriptorOwner()
        except Exception as e:
            return '?\\?'

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
    logger = logging.getLogger()
    all_perms = {}
    mask = win32security.OWNER_SECURITY_INFORMATION | win32security.GROUP_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    try:
        sd = win32security.GetFileSecurity(file, mask)
        ownersid = sd.GetSecurityDescriptorOwner()
        dacl = sd.GetSecurityDescriptorDacl()
    except:
        #   Si l'utilisateur n'a pas les droits nécessaires pour lire les infos ça plante...
        return {'DCO-FR\\GR_VTB': (0, (0, 0))}

    count = dacl.GetAceCount()
    for i in range(count):
        ace = dacl.GetAce(i)
        #   ace[0][0] = 1 signifie refus
        try:
            user, domain, int = win32security.LookupAccountSid(None, ace[2])
            all_perms[domain + "\\" + user] = (ace[1], ace[0])
        except:
            all_perms['Domaine\\%s' % ace[2]] = (ace[1], ace[0])
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
def get_perm(file, infos_serveur={}):
    logger = logging.getLogger()
    perm_list = []
    all_perms = fileperm_get_perms(file)
    for (domain_id, perm) in all_perms.items():
        mask = perm[0]
        type_perm = 'REFUS' if perm[1][0] == 1 else ''
        sys_id = domain_id.split('\\')[1]
        #   sys_id = str(sys_id)
        mask_name = get_mask(mask)

        if infos_serveur:
            if sys_id.lower() in infos_serveur['users']:
                grp_ou_usr = 'U'
            else:
                if sys_id.lower() in infos_serveur['groups']:
                    grp_ou_usr = 'G'
                else:
                    grp_ou_usr = '?'
        else:
            grp_ou_usr = ''

        perm_list.append([sys_id.lower(), mask_name, type_perm, perm[0], perm[1][0], perm[1][1], grp_ou_usr])

    perm_list.sort(key=lambda x: [x[6], x[0]])

    return perm_list


#   -----------------------------------------------------------------------
def remove_perm(file, *users, verbose=0):
    """
    Inspiré de http://stackoverflow.com/questions/26465546/how-to-authorize-deny-write-access-to-a-directory-on-windows-using-python
    Syntaxe :
        remove_perm('file', 'u1', 'u2', ..., 'un', verbose=x)
        OU
        remove_perm('file', *['u1', 'u2', ..., 'un'], verbose=x)
        OU
        remove_perm('file', *('u1', 'u2', ..., 'un'), verbose=x)
    """
    logger = logging.getLogger()

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
            logger.error('Erreur: %s' % traceback.format_exc())
            user = '%s' % ace[2]

        if user.lower() in users:
            if verbose:
                try:
                    print('On supprime %s pour %s' % (user, file))
                except UnicodeEncodeError:
                    texte_remplacement = ''.join([file[i] if ord(file[i]) < 255 else '¶' for i in range(len(file))])
                    print('On supprime %s pour %s' % (user, texte_remplacement))
            a_supprimer.append(i)

    a_supprimer.reverse()
    #   Super important, le reverse, si on supprime plusieurs éléments !
    for i in a_supprimer:
        dacl.DeleteAce(i)

    if a_supprimer:
        sd.SetSecurityDescriptorDacl(1, dacl, 0)   # may not be necessary
        win32security.SetFileSecurity(file, win32security.DACL_SECURITY_INFORMATION, sd)


#   -----------------------------------------------------------------------
def add_perm(file, permission, *users):
    """

        ATTENTION : expérimental. Peut mettre le bordel dans les héritages.

        Inspiré de http://stackoverflow.com/questions/28302666/impersonation-for-windows-in-python-3-using-win32security
        Syntaxe :
        add_perm('file', permission, 'u1', 'u2', ..., 'un')
        OU
        add_perm('file', permission, *['u1', 'u2', ..., 'un'])
        OU
        add_perm('file', permission, *('u1', 'u2', ..., 'un'))
    """
    logger = logging.getLogger()

    mask = win32security.OWNER_SECURITY_INFORMATION | win32security.GROUP_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    sd = win32security.GetFileSecurity(file, mask)
    ownersid = sd.GetSecurityDescriptorOwner()
    dacl = sd.GetSecurityDescriptorDacl()
    heritage = win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE | win32security.INHERITED_ACE

    for u in users:
        sid, domain, type = win32security.LookupAccountName('', u)
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, heritage, permission, sid)

    sd.SetSecurityDescriptorDacl(1, dacl, 0)

    win32security.SetFileSecurity(file, win32security.DACL_SECURITY_INFORMATION, sd)


#   -----------------------------------------------------------------------
def add_perm_by_sid(file, permission, *sidlist):
    """

        Identique à add_perm, mais au lieu de passer une liste d'utilisateurs en français on passe
        une liste de sid. Pour ne pas faire trois millions d'appels à win32security.LookupAccountName
        quand on traite une arborescence.

        Est-ce que ça vaut vraiment le coup ? un appel à win32security.LookupAccountName prend 3 ms.
    """
    logger = logging.getLogger()

    mask = win32security.OWNER_SECURITY_INFORMATION | win32security.GROUP_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    sd = win32security.GetFileSecurity(file, mask)
    ownersid = sd.GetSecurityDescriptorOwner()
    dacl = sd.GetSecurityDescriptorDacl()
    heritage = win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE | win32security.INHERITED_ACE

    for sid in sidlist:
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, heritage, permission, sid)

    sd.SetSecurityDescriptorDacl(1, dacl, 0)

    win32security.SetFileSecurity(file, win32security.DACL_SECURITY_INFORMATION, sd)


#   -----------------------------------------------------------------------
def get_user_s_perm(file, user, user_info):
    """
        Renseigne sur les droits d'accès d'un utilisateur sur un fichier.
        Pour commencer on fait simple, ça renvoie 0 (aucun droit), 1 (lecture)
        ou 2 (écriture).
        Et on considère que ces droits sont hiérarchisé. En fait on pourrait très bien autoriser
        l'écriture mais interdire la lecture. Dans la pratique ça marche quand même pas terrible.

        Pour une vue d'ensemble ça suffit.

        Amélioration à prévoir : indiquer en plus si l'autorisation est donnée individuellement
        ou par appartenance à un groupe.

        Par précaution en pensant aux futures évolutions on renvoie dès maintenant une liste.

        Arguments :
            file = nom du fichier
            user = nom de l'utilisateur
            user_info = objet UserInfo défini dans gipkouserinfo. Cet objet contient la liste
                        des utilisateurs et des groupes définis dans un serveur AD avec la
                        liste des groupes auxquel appartient chaque utilisateur.
    """
    users_groups = user_info.get_user_s_groups(user)
    file_perms = get_perm(file)
    liste_utile = [e for e in file_perms if (e[0] in users_groups or e[0] == user.lower())]
    liste_utile.sort(key=lambda x: x[4], reverse=True)
    #   Comme ça s'il y a des ACE de type "refus" on les traitera en premier. Comme windows...

    niveau = 0  # Le niveau d'autorisation qu'on renverra
    niveau_max = 2  # Oui, en dur, parce que c'est comme ça dans windows : 1 = lecture, 2 = écriture.

    for perm in liste_utile:
        if perm[4] is 1:
            #   On est dans les refus
            if (perm[3] & 2) and niveau_max > 1:
                #   Ecriture interdite...
                #   Et comme on peut avoir plusieurs ACE de refus successifs on va pas
                #   remonter le niveau.
                niveau_max = 1

            if perm[3] & 1:
                #   Lecture interdite. En toute rigueur lecture interdite + écriture autorisée
                #   l'utilisateur peut créer un nouveau fichier.
                #   Mais on a dit qu'on restait dans la simplicité.
                niveau_max = 0
                break
                #   Pas la peine de continuer, il a aucun accès.

        else:
            #   On traite les autorisations
            for i in range(1, 3):
                if niveau < perm[3] & i <= niveau_max:
                    niveau = perm[3] & i

        if niveau >= niveau_max:
            break

    return [niveau]


#   -----------------------------------------------------------------------
def get_tree_size(dir):
    if not os.path.isdir(dir):
        raise NotADirectoryError('%s n\est pas un répertoire' % dir)

    logger = logging.getLogger()
    taille = 0
    for D, dirs, fics in os.walk(dir):
        for f in fics:
            try:
                #   Parce qu'on n'est pas sûr d'avoir un accès autorisé partout...
                #   Ou qu'on est pas à l'abri d'un nom trop long !
                taille += os.path.getsize(os.path.join(D, f))
            except Exception as e:
                logger.error(e)

    return taille


#   -----------------------------------------------------------------------
def affichageHumain(taille):
    prefixes = ['o', 'ko', 'Mo', 'Go', 'To', 'Po', 'Eo', 'Zo', 'Yo']
    facteur = 1000
    n = 0
    while taille > facteur and n < len(prefixes) - 1:
        taille = taille / facteur
        n += 1

    return '%s %s' % (locale.format('%3.1f', taille, True), prefixes[n])


# ------------------------------------------------------------------------------------
def dateISO(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


# ------------------------------------------------------------------------------------
def get_file_dates(nomfic):
    return {'c': os.path.getctime(nomfic), 'a': os.path.getatime(nomfic), 'm': os.path.getmtime(nomfic)}


# ------------------------------------------------------------------------------------
def print_file_dates(nomfic, formatISO=False):
    dates = get_file_dates(nomfic)
    for cle in dates:
        print('%s : %s' % (cle, dateISO(dates[cle]) if formatISO else dates[cle]))


# ------------------------------------------------------------------------------------
def set_file_dates(nomfic, modified, accessed=None, formatISO=False):
    if accessed is None:
        accessed = modified

    if formatISO:
        modified = datetime.datetime.strptime(modified, '%Y-%m-%d %H:%M:%S').timestamp()
        accessed = datetime.datetime.strptime(accessed, '%Y-%m-%d %H:%M:%S').timestamp()

    os.utime(nomfic, (accessed, modified))


# ------------------------------------------------------------------------------------
